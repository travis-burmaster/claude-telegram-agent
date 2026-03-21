"""Tests for the agent spawner."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_agent_os.agents.spawner import (
    AgentPool,
    AgentResult,
    build_claude_command,
)


class TestBuildClaudeCommand:
    def test_basic_command(self):
        cmd = build_claude_command("Hello")
        assert cmd == ["claude", "--print", "--dangerously-skip-permissions", "-p", "Hello"]

    def test_workspace_not_in_command(self):
        """Workspace is passed as cwd to subprocess, not as a CLI flag."""
        cmd = build_claude_command("Hello")
        assert "--cwd" not in cmd

    def test_with_model(self):
        cmd = build_claude_command("Hello", model="claude-opus-4")
        assert "--model" in cmd
        assert "claude-opus-4" in cmd

    def test_without_skip_permissions(self):
        cmd = build_claude_command("Hello", skip_permissions=False)
        assert "--dangerously-skip-permissions" not in cmd

    def test_all_options(self):
        cmd = build_claude_command(
            "Do stuff",
            model="claude-opus-4",
            skip_permissions=True,
        )
        assert cmd[0] == "claude"
        assert "--print" in cmd
        assert "--dangerously-skip-permissions" in cmd
        assert "--model" in cmd
        assert "claude-opus-4" in cmd
        assert cmd[-2:] == ["-p", "Do stuff"]

    def test_prompt_is_last(self):
        cmd = build_claude_command("My prompt", model="m")
        assert cmd[-2] == "-p"
        assert cmd[-1] == "My prompt"


class TestAgentResult:
    def test_dataclass_fields(self):
        result = AgentResult(
            task_id="t-001",
            output="done",
            exit_code=0,
            duration=1.5,
        )
        assert result.task_id == "t-001"
        assert result.output == "done"
        assert result.exit_code == 0
        assert result.duration == 1.5


class TestAgentPool:
    def test_initial_active_count(self):
        pool = AgentPool(max_concurrent=3)
        assert pool.active_count() == 0

    @pytest.mark.asyncio
    async def test_spawn_returns_result(self):
        pool = AgentPool(max_concurrent=3)

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"output text", None))
        mock_proc.returncode = 0
        mock_proc.kill = AsyncMock()
        mock_proc.wait = AsyncMock()

        with patch("claude_agent_os.agents.spawner.asyncio.create_subprocess_exec",
                    return_value=mock_proc):
            result = await pool.spawn("t-001", "test prompt")
            assert isinstance(result, AgentResult)
            assert result.task_id == "t-001"
            assert result.output == "output text"
            assert result.exit_code == 0
            assert result.duration > 0

    @pytest.mark.asyncio
    async def test_spawn_timeout(self):
        pool = AgentPool(max_concurrent=3)

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError)
        mock_proc.kill = AsyncMock()
        mock_proc.wait = AsyncMock()

        with patch("claude_agent_os.agents.spawner.asyncio.create_subprocess_exec",
                    return_value=mock_proc):
            result = await pool.spawn("t-002", "slow prompt", timeout=1)
            assert result.exit_code == -1
            assert "timed out" in result.output

    @pytest.mark.asyncio
    async def test_active_count_during_execution(self):
        pool = AgentPool(max_concurrent=3)
        count_during = None

        async def slow_communicate():
            nonlocal count_during
            count_during = pool.active_count()
            return (b"done", None)

        mock_proc = AsyncMock()
        mock_proc.communicate = slow_communicate
        mock_proc.returncode = 0

        with patch("claude_agent_os.agents.spawner.asyncio.create_subprocess_exec",
                    return_value=mock_proc):
            await pool.spawn("t-003", "prompt")
            assert count_during == 1
            assert pool.active_count() == 0

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_returns_false(self):
        pool = AgentPool(max_concurrent=3)
        result = await pool.cancel("nonexistent")
        assert result is False

    def test_max_concurrent_stored(self):
        pool = AgentPool(max_concurrent=5)
        assert pool.max_concurrent == 5
