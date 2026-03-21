"""Tests for config loading and saving."""

import os
from pathlib import Path

import yaml
import pytest

from claude_agent_os.config import (
    AgentConfig,
    AgentCfg,
    WebCfg,
    TelegramCfg,
    load_config,
    save_config,
    DEFAULT_DATA_DIR,
)


class TestLoadConfigDefaults:
    """Test loading config with no config.yaml present."""

    def test_returns_agent_config(self, tmp_data_dir):
        cfg = load_config(data_dir=tmp_data_dir)
        assert isinstance(cfg, AgentConfig)

    def test_default_agent_name(self, tmp_data_dir):
        cfg = load_config(data_dir=tmp_data_dir)
        assert cfg.agent.name == "Claude Agent OS"

    def test_default_model(self, tmp_data_dir):
        cfg = load_config(data_dir=tmp_data_dir)
        assert cfg.agent.model == "claude-sonnet-4-6"

    def test_default_web_port(self, tmp_data_dir):
        cfg = load_config(data_dir=tmp_data_dir)
        assert cfg.web.port == 8420

    def test_paths_resolved_to_data_dir(self, tmp_data_dir):
        cfg = load_config(data_dir=tmp_data_dir)
        assert cfg.paths.soul == tmp_data_dir / "soul.md"
        assert cfg.paths.memory == tmp_data_dir / "memory"
        assert cfg.paths.tasks == tmp_data_dir / "tasks"

    def test_data_dir_stored(self, tmp_data_dir):
        cfg = load_config(data_dir=tmp_data_dir)
        assert cfg.data_dir == tmp_data_dir


class TestLoadConfigFromFile:
    """Test loading config from an existing config.yaml."""

    def test_loads_custom_values(self, tmp_data_dir):
        config_path = tmp_data_dir / "config.yaml"
        config_path.write_text(yaml.dump({
            "agent": {"name": "My Bot", "model": "claude-opus-4"},
            "web": {"port": 9999},
        }))
        cfg = load_config(data_dir=tmp_data_dir)
        assert cfg.agent.name == "My Bot"
        assert cfg.agent.model == "claude-opus-4"
        assert cfg.web.port == 9999

    def test_ignores_unknown_keys(self, tmp_data_dir):
        config_path = tmp_data_dir / "config.yaml"
        config_path.write_text(yaml.dump({
            "agent": {"name": "Bot", "unknown_field": "ignored"},
        }))
        cfg = load_config(data_dir=tmp_data_dir)
        assert cfg.agent.name == "Bot"

    def test_partial_config_keeps_defaults(self, tmp_data_dir):
        config_path = tmp_data_dir / "config.yaml"
        config_path.write_text(yaml.dump({"agent": {"name": "Custom"}}))
        cfg = load_config(data_dir=tmp_data_dir)
        assert cfg.agent.name == "Custom"
        assert cfg.agent.max_concurrent_agents == 3  # default preserved
        assert cfg.web.host == "127.0.0.1"  # default preserved


class TestEnvOverride:
    """Test environment variable overrides."""

    def test_telegram_token_from_env(self, tmp_data_dir, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token-123")
        cfg = load_config(data_dir=tmp_data_dir)
        assert cfg.telegram.bot_token == "test-token-123"

    def test_env_overrides_file(self, tmp_data_dir, monkeypatch):
        config_path = tmp_data_dir / "config.yaml"
        config_path.write_text(yaml.dump({
            "telegram": {"bot_token": "file-token"},
        }))
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "env-token")
        cfg = load_config(data_dir=tmp_data_dir)
        assert cfg.telegram.bot_token == "env-token"


class TestSaveConfig:
    """Test saving config back to disk."""

    def test_save_creates_file(self, tmp_data_dir):
        cfg = load_config(data_dir=tmp_data_dir)
        save_config(cfg)
        assert (tmp_data_dir / "config.yaml").exists()

    def test_round_trip(self, tmp_data_dir):
        cfg = load_config(data_dir=tmp_data_dir)
        cfg.agent.name = "Round Trip Bot"
        cfg.web.port = 1234
        save_config(cfg)

        cfg2 = load_config(data_dir=tmp_data_dir)
        assert cfg2.agent.name == "Round Trip Bot"
        assert cfg2.web.port == 1234

    def test_save_creates_parent_dirs(self, tmp_path):
        nested = tmp_path / "a" / "b" / "c"
        cfg = load_config(data_dir=nested)
        save_config(cfg)
        assert (nested / "config.yaml").exists()
