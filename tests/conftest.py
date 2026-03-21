"""Shared fixtures for claude-agent-os tests."""

import pytest
from pathlib import Path

from claude_agent_os.config import AgentConfig, load_config


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """Create a temporary data directory for tests."""
    data_dir = tmp_path / "agent-os-data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def sample_config(tmp_data_dir: Path) -> AgentConfig:
    """Load a default config pointing at the tmp data dir."""
    return load_config(data_dir=tmp_data_dir)
