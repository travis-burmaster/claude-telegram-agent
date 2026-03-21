"""Claude Code subprocess spawner with pool-based concurrency limits."""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentResult:
    """Result from a spawned Claude agent."""
    task_id: str
    output: str
    exit_code: int
    duration: float


def build_claude_command(
    prompt: str,
    workspace: str | None = None,
    model: str | None = None,
    skip_permissions: bool = True,
) -> list[str]:
    """Build a claude CLI command list."""
    cmd = ["claude", "--print"]
    if skip_permissions:
        cmd.append("--dangerously-skip-permissions")
    if workspace:
        cmd.extend(["--cwd", workspace])
    if model:
        cmd.extend(["--model", model])
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
            cmd = build_claude_command(prompt, workspace=workspace, model=model)
            start = time.monotonic()

            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
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
