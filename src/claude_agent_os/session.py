from __future__ import annotations
"""Managed Claude Code session — single long-running subprocess with monitoring.

Uses a pseudo-TTY so the Claude CLI runs in interactive mode, which is required
for channel plugins (like Telegram) to inject messages via MCP notifications.
"""

import asyncio
import fcntl
import logging
import os
import pty
import signal
import struct
import termios
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable

from claude_agent_os.config import AgentConfig

logger = logging.getLogger(__name__)

# Max log lines kept in memory for the dashboard
LOG_BUFFER_SIZE = 2000

# If no output for this many seconds, mark as "stuck"
STUCK_TIMEOUT_SECONDS = 300  # 5 minutes


class SessionState(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STUCK = "stuck"
    CRASHED = "crashed"
    STOPPING = "stopping"


@dataclass
class LogEntry:
    timestamp: float
    stream: str  # "stdout" or "stderr"
    line: str


@dataclass
class SessionInfo:
    state: SessionState = SessionState.STOPPED
    pid: int | None = None
    started_at: float | None = None
    last_output_at: float | None = None
    exit_code: int | None = None
    restart_count: int = 0


class SessionManager:
    """Manages a single Claude Code + Telegram session as a supervised subprocess.

    Runs the claude CLI under a pseudo-TTY so it stays in interactive mode,
    allowing channel plugins (Telegram) to inject messages via MCP notifications.
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.info = SessionInfo()
        self._pid: int | None = None
        self._master_fd: int | None = None
        self._log_buffer: deque[LogEntry] = deque(maxlen=LOG_BUFFER_SIZE)
        self._log_file: Path | None = None
        self._monitor_task: asyncio.Task | None = None
        self._read_task: asyncio.Task | None = None
        self._subscribers: list[asyncio.Queue[LogEntry]] = []
        self._lock = asyncio.Lock()

    # ── Build command ────────────────────────────────────────────────

    def _build_command(self) -> list[str]:
        """Build the claude CLI command for the managed Telegram session."""
        cmd = [
            "claude",
            "--dangerously-skip-permissions",
        ]

        if self.config.agent.model:
            cmd.extend(["--model", self.config.agent.model])

        # Inject soul + memory awareness via system prompt
        system_ctx = self._build_system_context()
        if system_ctx:
            cmd.extend(["--append-system-prompt", system_ctx])

        return cmd

    def _build_system_context(self) -> str:
        """Build system prompt supplement with soul and memory pointers."""
        parts: list[str] = []
        data_dir = self.config.data_dir

        # Critical: Telegram reply instructions
        # The managed session's sole purpose is to handle Telegram messages.
        # Messages arrive via the Telegram channel plugin, but may not always
        # include the <channel> tag. Since this session ONLY receives Telegram
        # messages, ALL user messages must be responded to via the
        # mcp__plugin_telegram_telegram__reply tool — NEVER by outputting text
        # to the terminal. Look up the chat_id from the <channel> tag if
        # present, otherwise use the most recently seen chat_id.
        parts.append(
            "# CRITICAL: Telegram Response Rule\n"
            "This is a dedicated Telegram agent session. Every user message you\n"
            "receive comes from Telegram. You MUST respond using the\n"
            "mcp__plugin_telegram_telegram__reply tool — NEVER output text to the\n"
            "terminal. If the message has a <channel> tag, use the chat_id from it.\n"
            "If it does not, use the chat_id from the most recent <channel> tag you\n"
            "have seen, or the configured allowed user's chat_id.\n"
            f"Default chat_id (from config): {self.config.telegram.allowed_users[0] if self.config.telegram.allowed_users else 'unknown'}"
        )

        # Soul
        soul_path = self.config.paths.soul
        if soul_path.exists():
            parts.append(f"# Soul\n{soul_path.read_text().strip()}")

        # Data directory awareness
        parts.append(
            f"# Your persistent data directory: {data_dir}\n"
            "You are a persistent agent managed by Claude Agent OS.\n"
            "Key paths:\n"
            f"  soul:    {self.config.paths.soul}\n"
            f"  memory:  {self.config.paths.memory}/\n"
            f"  tasks:   {self.config.paths.tasks}/\n"
            f"  cron:    {self.config.paths.cron}/\n"
            f"  logs:    {self.config.paths.logs}/\n"
            f"  config:  {data_dir / 'config.yaml'}"
        )

        # Memory index summary
        memory_index = self.config.paths.memory / "index.json"
        if memory_index.exists():
            try:
                import json
                index = json.loads(memory_index.read_text())
                if index:
                    lines = [f"# Memories ({len(index)} total)"]
                    for entry in index[:20]:
                        lines.append(
                            f"  - [{entry.get('type', '?')}] {entry.get('name', '?')} "
                            f"(tags: {', '.join(entry.get('tags', []))})"
                        )
                    if len(index) > 20:
                        lines.append(f"  ... and {len(index) - 20} more")
                    parts.append("\n".join(lines))
            except Exception:
                pass

        return "\n\n".join(parts)

    # ── Trust dialog handling ───────────────────────────────────────

    async def _auto_accept_trust_dialog(self) -> None:
        """Wait for the workspace trust dialog and send Enter to accept.

        The Claude CLI shows a trust dialog in interactive mode with option
        '1. Yes, I trust this folder' pre-selected. We wait for it to appear
        then send Enter to accept.
        """
        if self._master_fd is None:
            return

        # Read PTY output until we see the trust dialog or timeout
        buf = b""
        deadline = time.time() + 15  # 15 second timeout
        while time.time() < deadline:
            try:
                os.set_blocking(self._master_fd, False)
                try:
                    chunk = os.read(self._master_fd, 4096)
                    if chunk:
                        buf += chunk
                        text = buf.decode("utf-8", errors="replace")
                        # Log the startup output
                        for line in text.split("\n"):
                            stripped = line.strip()
                            if stripped:
                                entry = LogEntry(
                                    timestamp=time.time(), stream="stdout", line=stripped
                                )
                                self._log_buffer.append(entry)
                                self.info.last_output_at = entry.timestamp
                                if self._log_file:
                                    try:
                                        with open(self._log_file, "a") as f:
                                            f.write(f"{stripped}\n")
                                    except Exception:
                                        pass

                        if "trust" in text.lower() and ("enter" in text.lower() or "confirm" in text.lower()):
                            logger.info("Trust dialog detected, sending Enter to accept")
                            await asyncio.sleep(0.5)
                            os.write(self._master_fd, b"\r")
                            # Give it a moment to process
                            await asyncio.sleep(2)
                            # Drain any remaining startup output
                            try:
                                os.set_blocking(self._master_fd, False)
                                remaining = os.read(self._master_fd, 8192)
                                if remaining:
                                    for line in remaining.decode("utf-8", errors="replace").split("\n"):
                                        stripped = line.strip()
                                        if stripped:
                                            entry = LogEntry(
                                                timestamp=time.time(), stream="stdout", line=stripped
                                            )
                                            self._log_buffer.append(entry)
                                            self.info.last_output_at = entry.timestamp
                                            if self._log_file:
                                                try:
                                                    with open(self._log_file, "a") as f:
                                                        f.write(f"{stripped}\n")
                                                except Exception:
                                                    pass
                            except (OSError, BlockingIOError):
                                pass
                            return
                except (BlockingIOError, OSError):
                    pass
            except Exception as e:
                logger.error("Error during trust dialog handling: %s", e)
                break
            await asyncio.sleep(0.3)

        logger.info("No trust dialog detected (may already be trusted), continuing")

    # ── Lifecycle ────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the Claude Code session under a pseudo-TTY."""
        async with self._lock:
            if self.info.state in (SessionState.RUNNING, SessionState.STARTING):
                logger.warning("Session already %s", self.info.state)
                return

            self.info.state = SessionState.STARTING
            self.info.exit_code = None

            cmd = self._build_command()
            logger.info("Starting session: %s", " ".join(cmd[:6]) + " ...")

            # Open log file
            self.config.paths.logs.mkdir(parents=True, exist_ok=True)
            self._log_file = self.config.paths.logs / "session.log"

            workspace = (
                Path(self.config.agent.workspace).expanduser()
                if self.config.agent.workspace
                else Path.home()
            )

            try:
                # Fork with a pseudo-TTY so claude runs in interactive mode
                pid, master_fd = pty.fork()
            except OSError as e:
                self.info.state = SessionState.CRASHED
                logger.error("Failed to fork PTY: %s", e)
                return

            if pid == 0:
                # ── Child process ──
                os.chdir(str(workspace))
                os.environ["TERM"] = "xterm-256color"
                # Ensure claude can find tools in PATH
                path = os.environ.get("PATH", "")
                if "/opt/homebrew/bin" not in path:
                    os.environ["PATH"] = f"/opt/homebrew/bin:/opt/homebrew/sbin:{path}"
                try:
                    os.execvp(cmd[0], cmd)
                except FileNotFoundError:
                    os._exit(127)
                except Exception:
                    os._exit(1)
            else:
                # ── Parent process ──
                self._pid = pid
                self._master_fd = master_fd

                # Set a reasonable terminal size (rows, cols) so the CLI
                # doesn't hang or misbehave with a 0x0 default PTY size.
                try:
                    winsize = struct.pack("HHHH", 50, 120, 0, 0)
                    fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
                except OSError:
                    pass

                now = time.time()
                self.info.pid = pid
                self.info.started_at = now
                self.info.last_output_at = now
                self.info.state = SessionState.RUNNING

                # Auto-accept the workspace trust dialog by sending Enter
                # after a brief delay (the dialog defaults to "Yes, I trust")
                await self._auto_accept_trust_dialog()

                # Make master_fd non-blocking for async reading
                os.set_blocking(master_fd, False)

                # Start PTY output reader
                self._read_task = asyncio.create_task(self._read_pty_output())

                # Start health monitor
                self._monitor_task = asyncio.create_task(self._monitor_loop())

                logger.info("Session started (pid=%s)", self.info.pid)

    async def stop(self) -> None:
        """Gracefully stop the session."""
        async with self._lock:
            await self._stop_internal()

    async def _stop_internal(self) -> None:
        """Internal stop without lock (called from within locked contexts)."""
        if self._pid is None:
            self.info.state = SessionState.STOPPED
            return

        self.info.state = SessionState.STOPPING
        logger.info("Stopping session (pid=%s)", self.info.pid)

        try:
            os.kill(self._pid, signal.SIGTERM)
            # Wait for process to exit
            for _ in range(20):  # 10 seconds max
                try:
                    wpid, status = os.waitpid(self._pid, os.WNOHANG)
                    if wpid != 0:
                        self.info.exit_code = os.WEXITSTATUS(status) if os.WIFEXITED(status) else -1
                        break
                except ChildProcessError:
                    break
                await asyncio.sleep(0.5)
            else:
                # Force kill
                logger.warning("Session didn't terminate gracefully, killing")
                try:
                    os.kill(self._pid, signal.SIGKILL)
                    os.waitpid(self._pid, 0)
                except (ProcessLookupError, ChildProcessError):
                    pass
        except ProcessLookupError:
            pass  # already dead

        # Close PTY master fd
        if self._master_fd is not None:
            try:
                os.close(self._master_fd)
            except OSError:
                pass
            self._master_fd = None

        self.info.state = SessionState.STOPPED
        self.info.pid = None
        self._pid = None

        # Cancel reader/monitor tasks
        if self._read_task:
            self._read_task.cancel()
            self._read_task = None

        if self._monitor_task:
            self._monitor_task.cancel()
            self._monitor_task = None

        logger.info("Session stopped (exit_code=%s)", self.info.exit_code)

    async def restart(self) -> None:
        """Stop and restart the session."""
        async with self._lock:
            await self._stop_internal()
            self.info.restart_count += 1

        await self.start()
        logger.info("Session restarted (restart_count=%s)", self.info.restart_count)

    # ── PTY output reading ───────────────────────────────────────────

    async def _read_pty_output(self) -> None:
        """Read output from the PTY master fd and dispatch to log buffer + subscribers."""
        loop = asyncio.get_event_loop()

        try:
            while True:
                try:
                    data = await loop.run_in_executor(None, self._blocking_read)
                    if not data:
                        break

                    # Strip ANSI escape sequences for cleaner logging
                    text = data.decode("utf-8", errors="replace")
                    # Update last_output_at on any data received
                    self.info.last_output_at = time.time()

                    # Split into lines (handle both \n and \r\n)
                    for line in text.split("\n"):
                        line = line.rstrip("\r")
                        if not line:
                            continue

                        entry = LogEntry(timestamp=time.time(), stream="stdout", line=line)
                        self._log_buffer.append(entry)

                        # Write to log file
                        if self._log_file:
                            try:
                                with open(self._log_file, "a") as f:
                                    f.write(f"{line}\n")
                            except Exception:
                                pass

                        # Push to live subscribers
                        dead: list[int] = []
                        for i, queue in enumerate(self._subscribers):
                            try:
                                queue.put_nowait(entry)
                            except asyncio.QueueFull:
                                dead.append(i)
                        for i in reversed(dead):
                            self._subscribers.pop(i)

                except OSError:
                    break

        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.error("PTY reader error: %s", e)

        # PTY closed — check if process is still alive
        self._check_child_exit()

    def _blocking_read(self) -> bytes:
        """Blocking read from PTY master fd. Runs in executor thread."""
        if self._master_fd is None:
            return b""
        try:
            # Re-enable blocking for this thread-based read
            os.set_blocking(self._master_fd, True)
            return os.read(self._master_fd, 4096)
        except OSError:
            return b""

    def _check_child_exit(self) -> None:
        """Check if the child process has exited and update state."""
        if self._pid is None:
            return
        try:
            wpid, status = os.waitpid(self._pid, os.WNOHANG)
            if wpid != 0:
                self.info.exit_code = os.WEXITSTATUS(status) if os.WIFEXITED(status) else -1
                if self.info.state == SessionState.RUNNING:
                    self.info.state = SessionState.CRASHED
                    logger.warning("Session exited unexpectedly (code=%s)", self.info.exit_code)
        except ChildProcessError:
            if self.info.state == SessionState.RUNNING:
                self.info.state = SessionState.CRASHED
                logger.warning("Session child process gone")

    # ── Health monitoring ────────────────────────────────────────────

    async def _monitor_loop(self) -> None:
        """Periodically check session health."""
        try:
            while True:
                await asyncio.sleep(30)

                if self.info.state != SessionState.RUNNING:
                    continue

                # Check if process is still alive
                self._check_child_exit()
                if self.info.state != SessionState.RUNNING:
                    continue

                # Check for stuck state (no output for too long)
                if self.info.last_output_at:
                    silence = time.time() - self.info.last_output_at
                    if silence > STUCK_TIMEOUT_SECONDS:
                        if self.info.state != SessionState.STUCK:
                            self.info.state = SessionState.STUCK
                            logger.warning("Session appears stuck (no output for %.0fs)", silence)
                    elif self.info.state == SessionState.STUCK:
                        # Recovered — got output again
                        self.info.state = SessionState.RUNNING
                        logger.info("Session recovered from stuck state")

        except asyncio.CancelledError:
            return

    # ── Log access ───────────────────────────────────────────────────

    def get_recent_logs(self, n: int = 100) -> list[dict]:
        """Return the most recent n log entries as dicts."""
        entries = list(self._log_buffer)[-n:]
        return [
            {"timestamp": e.timestamp, "stream": e.stream, "line": e.line}
            for e in entries
        ]

    def subscribe(self) -> asyncio.Queue[LogEntry]:
        """Create a live subscription queue for log entries."""
        queue: asyncio.Queue[LogEntry] = asyncio.Queue(maxsize=500)
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[LogEntry]) -> None:
        """Remove a subscription queue."""
        try:
            self._subscribers.remove(queue)
        except ValueError:
            pass

    # ── Status ───────────────────────────────────────────────────────

    def status(self) -> dict:
        """Return current session status as a dict."""
        now = time.time()
        uptime = None
        if self.info.started_at and self.info.state in (
            SessionState.RUNNING, SessionState.STUCK
        ):
            uptime = now - self.info.started_at

        silence = None
        if self.info.last_output_at:
            silence = now - self.info.last_output_at

        return {
            "state": self.info.state.value,
            "pid": self.info.pid,
            "started_at": self.info.started_at,
            "uptime_seconds": uptime,
            "last_output_at": self.info.last_output_at,
            "silence_seconds": silence,
            "exit_code": self.info.exit_code,
            "restart_count": self.info.restart_count,
            "log_lines_buffered": len(self._log_buffer),
        }
