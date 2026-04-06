from __future__ import annotations
"""Claude Code subprocess spawner with pool-based concurrency limits.

Supports two execution modes:
1. Local Claude CLI subprocess (default)
2. HTTP proxy fallback (for OAuth-backed local proxies like swarm-proxy)
"""

import asyncio
import logging
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DATA_DIR = Path.home() / ".claude-agent-os"
DEFAULT_CLAUDE_PATHS = [
    "/home/tadmin/.npm-global/bin/claude",
    "/opt/homebrew/bin/claude",
    "/usr/local/bin/claude",
    "/usr/bin/claude",
]


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

    soul_path = data_dir / "soul.md"
    if soul_path.exists():
        parts.append(f"# Soul\n{soul_path.read_text().strip()}")

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

    conversation_db = data_dir / "memory" / "conversation.db"
    try:
        from claude_agent_os.conversation import get_recent_context
        convo_text = get_recent_context(conversation_db)
        if convo_text:
            parts.append(
                "# Recent Conversation Context\n"
                "Below is a log of recent interactions between Travis and Claude "
                "in the CLI. Use this to understand what's being worked on and "
                "maintain continuity.\n\n" + convo_text
            )
    except Exception as e:
        logger.warning("Failed to read conversation DB: %s", e)

    memory_index = data_dir / "memory" / "index.json"
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
                lines.append(
                    f"\nTo read a memory, read the file at {data_dir / 'memory/<type>/<name>.md'}"
                )
                parts.append("\n".join(lines))
        except Exception:
            pass

    return "\n\n".join(parts)


def resolve_claude_binary() -> str:
    """Resolve the Claude executable path robustly across shells/services."""
    found = shutil.which("claude")
    if found:
        return found
    for candidate in DEFAULT_CLAUDE_PATHS:
        if Path(candidate).exists():
            return candidate
    return "claude"


def build_claude_command(
    prompt: str,
    model: str | None = None,
    skip_permissions: bool = True,
) -> list[str]:
    """Build a claude CLI command list."""
    cmd = [resolve_claude_binary(), "--print"]
    if skip_permissions:
        cmd.append("--dangerously-skip-permissions")
    if model:
        cmd.extend(["--model", model])

    system_context = _build_system_context()
    if system_context:
        cmd.extend(["--append-system-prompt", system_context])

    cmd.extend(["-p", prompt])
    return cmd


async def _spawn_via_proxy(
    task_id: str,
    prompt: str,
    model: str | None,
    timeout: int,
) -> AgentResult:
    """Run an agent request through a local Claude-compatible proxy."""
    start = time.monotonic()
    proxy_url = os.environ.get("CLAUDE_PROXY_URL") or os.environ.get("SWARM_PROXY_URL")
    if not proxy_url:
        raise RuntimeError("Proxy mode requested but CLAUDE_PROXY_URL / SWARM_PROXY_URL not set")

    model = model or os.environ.get("CLAUDE_MODEL") or "claude-sonnet-4-6"
    system_context = _build_system_context()
    payload = {
        "model": model,
        "max_tokens": 2048,
        "system": system_context,
        "messages": [{"role": "user", "content": prompt}],
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(f"{proxy_url.rstrip('/')}/v1/messages", json=payload)
        resp.raise_for_status()
        data = resp.json()

    text_parts = []
    for item in data.get("content", []):
        if item.get("type") == "text":
            text_parts.append(item.get("text", ""))
    output = "\n".join(text_parts).strip()
    duration = time.monotonic() - start
    return AgentResult(task_id=task_id, output=output, exit_code=0, duration=duration)


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
        """Spawn a Claude agent subprocess, respecting pool limits.

        If CLAUDE_PROXY_URL or SWARM_PROXY_URL is set, prefer the HTTP proxy path.
        Otherwise use the local Claude CLI.
        """
        async with self._semaphore:
            start = time.monotonic()
            self._active[task_id] = asyncio.current_task()  # type: ignore[assignment]
            try:
                proxy_url = os.environ.get("CLAUDE_PROXY_URL") or os.environ.get("SWARM_PROXY_URL")
                if proxy_url:
                    logger.info("Spawning agent %s via proxy %s", task_id, proxy_url)
                    return await _spawn_via_proxy(task_id=task_id, prompt=prompt, model=model, timeout=timeout)

                cmd = build_claude_command(prompt, model=model)
                logger.info("Spawning agent %s via CLI: %s", task_id, cmd[0:4])

                env = os.environ.copy()
                env_path = env.get("PATH", "")
                extra = ["/home/tadmin/.npm-global/bin", "/usr/local/bin", "/usr/bin", "/bin"]
                for p in reversed(extra):
                    if p not in env_path:
                        env_path = f"{p}:{env_path}" if env_path else p
                env["PATH"] = env_path

                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    cwd=workspace,
                    env=env,
                )

                try:
                    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
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
