from __future__ import annotations
"""Claude Code subprocess spawner with pool-based concurrency limits."""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATA_DIR = Path.home() / ".claude-agent-os"


@dataclass
class AgentResult:
    """Result from a spawned Claude agent."""
    task_id: str
    output: str
    exit_code: int
    duration: float


def _build_system_context() -> str:
    """Build a system prompt supplement with soul, memories, and data dir awareness."""
    parts: list[str] = []
    data_dir = DATA_DIR

    # Soul
    soul_path = data_dir / "soul.md"
    if soul_path.exists():
        parts.append(f"# Soul\n{soul_path.read_text().strip()}")

    # Data directory map
    parts.append(f"# Your persistent data directory: {data_dir}")
    parts.append(
        "You are a persistent agent. Your files survive across sessions.\n"
        "Key paths:\n"
        f"  soul:    {data_dir / 'soul.md'} — your personality and instructions\n"
        f"  memory:  {data_dir / 'memory/'} — YAML-frontmatter markdown files organized by type\n"
        f"  tasks:   {data_dir / 'tasks/'} — task tracker (active.json)\n"
        f"  cron:    {data_dir / 'cron/'} — scheduled job definitions\n"
        f"  config:  {data_dir / 'config.yaml'} — server and channel config\n"
        f"  inbox:   {data_dir / 'inbox/'} — files received from Telegram\n"
        f"  logs:    {data_dir / 'logs/'} — agent output logs"
    )

    # Memory index summary
    memory_index = data_dir / "memory" / "index.json"
    if memory_index.exists():
        try:
            import json
            index = json.loads(memory_index.read_text())
            if index:
                lines = [f"# Memories ({len(index)} total)"]
                for entry in index[:20]:  # cap at 20 to keep prompt reasonable
                    lines.append(
                        f"  - [{entry.get('type', '?')}] {entry.get('name', '?')} "
                        f"(tags: {', '.join(entry.get('tags', []))})"
                    )
                if len(index) > 20:
                    lines.append(f"  ... and {len(index) - 20} more")
                lines.append(
                    f"\nTo read a memory, read the file at {data_dir / 'memory/<type>/<name>.md'}"
                )
                parts.append("\n".join(lines))
        except Exception:
            pass

    return "\n\n".join(parts)


def build_claude_command(
    prompt: str,
    model: str | None = None,
    skip_permissions: bool = True,
) -> list[str]:
    """Build a claude CLI command list."""
    cmd = ["claude", "--print"]
    if skip_permissions:
        cmd.append("--dangerously-skip-permissions")
    if model:
        cmd.extend(["--model", model])

    system_context = _build_system_context()
    if system_context:
        cmd.extend(["--append-system-prompt", system_context])

    cmd.extend(["-p", prompt])
    return cmd


class AgentPool:
    """Pool that limits concurrent Claude agent subprocesses."""

    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active: dict[str, asyncio.Task[Any]] = {}

    async def spawn(
        self,
        task_id: str,
        prompt: str,
        workspace: str | None = None,
        model: str | None = None,
        timeout: int = 600,
    ) -> AgentResult:
        """Spawn a Claude agent subprocess, respecting pool limits."""
        async with self._semaphore:
            cmd = build_claude_command(prompt, model=model)
            logger.info("Spawning agent %s: %s", task_id, cmd[0:4])
            start = time.monotonic()

            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    cwd=workspace,
                )
                # Store the task for potential cancellation
                self._active[task_id] = asyncio.current_task()  # type: ignore[assignment]

                try:
                    stdout, _ = await asyncio.wait_for(
                        proc.communicate(), timeout=timeout
                    )
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
                    duration = time.monotonic() - start
                    return AgentResult(
                        task_id=task_id,
                        output=f"Agent timed out after {timeout}s",
                        exit_code=-1,
                        duration=duration,
                    )

                duration = time.monotonic() - start
                return AgentResult(
                    task_id=task_id,
                    output=stdout.decode() if stdout else "",
                    exit_code=proc.returncode or 0,
                    duration=duration,
                )
            finally:
                self._active.pop(task_id, None)

    def active_count(self) -> int:
        """Return the number of currently active agents."""
        return len(self._active)

    async def cancel(self, task_id: str) -> bool:
        """Cancel a running agent task. Returns True if found and cancelled."""
        task = self._active.get(task_id)
        if task is not None:
            task.cancel()
            return True
        return False
