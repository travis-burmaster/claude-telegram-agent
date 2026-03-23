from __future__ import annotations
"""Managed Claude Code session — single long-running subprocess with monitoring."""

import asyncio
import logging
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
    """Manages a single Claude Code + Telegram session as a supervised subprocess."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.info = SessionInfo()
        self._process: asyncio.subprocess.Process | None = None
        self._log_buffer: deque[LogEntry] = deque(maxlen=LOG_BUFFER_SIZE)
        self._log_file: Path | None = None
        self._monitor_task: asyncio.Task | None = None
        self._read_tasks: list[asyncio.Task] = []
        self._subscribers: list[asyncio.Queue[LogEntry]] = []
        self._lock = asyncio.Lock()

    # ── Build command ────────────────────────────────────────────────

    def _build_command(self) -> list[str]:
        """Build the claude CLI command for the managed Telegram session."""
        cmd = [
            "claude",
            "--channels", "plugin:telegram@claude-plugins-official",
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

    # ── Lifecycle ────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the Claude Code session."""
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
                self._process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(workspace),
                )
            except FileNotFoundError:
                self.info.state = SessionState.CRASHED
                logger.error("'claude' not found in PATH")
                return
            except Exception as e:
                self.info.state = SessionState.CRASHED
                logger.error("Failed to start session: %s", e)
                return

            now = time.time()
            self.info.pid = self._process.pid
            self.info.started_at = now
            self.info.last_output_at = now
            self.info.state = SessionState.RUNNING

            # Start output readers
            self._read_tasks = [
                asyncio.create_task(self._read_stream("stdout", self._process.stdout)),
                asyncio.create_task(self._read_stream("stderr", self._process.stderr)),
            ]

            # Start health monitor
            self._monitor_task = asyncio.create_task(self._monitor_loop())

            logger.info("Session started (pid=%s)", self.info.pid)

    async def stop(self) -> None:
        """Gracefully stop the session."""
        async with self._lock:
            await self._stop_internal()

    async def _stop_internal(self) -> None:
        """Internal stop without lock (called from within locked contexts)."""
        if self._process is None:
            self.info.state = SessionState.STOPPED
            return

        self.info.state = SessionState.STOPPING
        logger.info("Stopping session (pid=%s)", self.info.pid)

        try:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=10)
            except asyncio.TimeoutError:
                logger.warning("Session didn't terminate gracefully, killing")
                self._process.kill()
                await self._process.wait()
        except ProcessLookupError:
            pass  # already dead

        self.info.exit_code = self._process.returncode
        self.info.state = SessionState.STOPPED
        self.info.pid = None
        self._process = None

        # Cancel reader/monitor tasks
        for task in self._read_tasks:
            task.cancel()
        self._read_tasks.clear()

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

    # ── Output streaming ─────────────────────────────────────────────

    async def _read_stream(self, stream_name: str, stream: asyncio.StreamReader) -> None:
        """Read lines from a subprocess stream and dispatch to log buffer + subscribers."""
        try:
            while True:
                line_bytes = await stream.readline()
                if not line_bytes:
                    break

                line = line_bytes.decode("utf-8", errors="replace").rstrip("\n")
                entry = LogEntry(timestamp=time.time(), stream=stream_name, line=line)

                self._log_buffer.append(entry)
                self.info.last_output_at = entry.timestamp

                # Write to log file
                if self._log_file:
                    try:
                        with open(self._log_file, "a") as f:
                            f.write(f"[{stream_name}] {line}\n")
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

        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.error("Stream reader error (%s): %s", stream_name, e)

        # Stream ended — check if process is still alive
        if self._process and self._process.returncode is not None:
            self.info.exit_code = self._process.returncode
            if self.info.state == SessionState.RUNNING:
                self.info.state = SessionState.CRASHED
                logger.warning("Session exited unexpectedly (code=%s)", self.info.exit_code)

    # ── Health monitoring ────────────────────────────────────────────

    async def _monitor_loop(self) -> None:
        """Periodically check session health."""
        try:
            while True:
                await asyncio.sleep(30)

                if self.info.state != SessionState.RUNNING:
                    continue

                # Check if process is still alive
                if self._process is None or self._process.returncode is not None:
                    self.info.state = SessionState.CRASHED
                    self.info.exit_code = self._process.returncode if self._process else None
                    logger.warning("Monitor detected session crash (code=%s)", self.info.exit_code)
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
