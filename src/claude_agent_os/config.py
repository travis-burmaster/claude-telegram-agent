from __future__ import annotations
"""Configuration loader for claude-agent-os."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
import os

DEFAULT_DATA_DIR = Path.home() / ".claude-agent-os"


@dataclass
class AgentCfg:
    name: str = "Claude Agent OS"
    model: str = "claude-sonnet-4-6"
    max_concurrent_agents: int = 3
    auto_pickup_tasks: bool = True
    workspace: str = ""  # working directory for the managed session (empty = home)


@dataclass
class WebCfg:
    host: str = "127.0.0.1"
    port: int = 8420
    password_hash: str = ""


@dataclass
class TelegramCfg:
    bot_token: str = ""
    allowed_users: list[str] = field(default_factory=list)


@dataclass
class NotificationsCfg:
    default_channel: str = "telegram"


@dataclass
class PathsCfg:
    soul: Path = field(default_factory=lambda: Path("soul.md"))
    memory: Path = field(default_factory=lambda: Path("memory"))
    tasks: Path = field(default_factory=lambda: Path("tasks"))
    cron: Path = field(default_factory=lambda: Path("cron"))
    logs: Path = field(default_factory=lambda: Path("logs"))


@dataclass
class AgentConfig:
    agent: AgentCfg = field(default_factory=AgentCfg)
    web: WebCfg = field(default_factory=WebCfg)
    telegram: TelegramCfg = field(default_factory=TelegramCfg)
    notifications: NotificationsCfg = field(default_factory=NotificationsCfg)
    paths: PathsCfg = field(default_factory=PathsCfg)
    data_dir: Path = field(default_factory=lambda: DEFAULT_DATA_DIR)


def _dataclass_from_dict(cls: type, data: dict[str, Any]) -> Any:
    """Recursively build a dataclass from a dict, ignoring unknown keys."""
    if not data:
        return cls()
    field_names = {f.name for f in cls.__dataclass_fields__.values()}
    filtered = {}
    for k, v in data.items():
        if k not in field_names:
            continue
        f = cls.__dataclass_fields__[k]
        if f.type is Path or f.type == Path or f.type == "Path":
            filtered[k] = Path(v)
        else:
            filtered[k] = v
    return cls(**filtered)


def load_config(data_dir: Path | str | None = None) -> AgentConfig:
    """Load config from config.yaml, falling back to defaults.

    Resolves relative paths against data_dir. Supports TELEGRAM_BOT_TOKEN
    env var override.
    """
    data_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
    config_path = data_dir / "config.yaml"

    cfg = AgentConfig(data_dir=data_dir)

    if config_path.exists():
        with open(config_path) as f:
            raw = yaml.safe_load(f) or {}

        if "agent" in raw:
            cfg.agent = _dataclass_from_dict(AgentCfg, raw["agent"])
        if "web" in raw:
            cfg.web = _dataclass_from_dict(WebCfg, raw["web"])
        if "telegram" in raw:
            cfg.telegram = _dataclass_from_dict(TelegramCfg, raw["telegram"])
        if "notifications" in raw:
            cfg.notifications = _dataclass_from_dict(NotificationsCfg, raw["notifications"])
        if "paths" in raw:
            cfg.paths = _dataclass_from_dict(PathsCfg, raw["paths"])

    # Env var override for telegram bot token
    env_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if env_token:
        cfg.telegram.bot_token = env_token

    # Resolve relative paths against data_dir
    for field_name in ("soul", "memory", "tasks", "cron", "logs"):
        p = getattr(cfg.paths, field_name)
        if not p.is_absolute():
            setattr(cfg.paths, field_name, data_dir / p)

    return cfg


def _dataclass_to_dict(obj: Any) -> dict[str, Any]:
    """Convert a dataclass to a dict, converting Paths to strings."""
    result = {}
    for f in obj.__dataclass_fields__.values():
        val = getattr(obj, f.name)
        if isinstance(val, Path):
            result[f.name] = str(val)
        elif hasattr(val, "__dataclass_fields__"):
            result[f.name] = _dataclass_to_dict(val)
        else:
            result[f.name] = val
    return result


def save_config(cfg: AgentConfig) -> None:
    """Write config back to config.yaml in data_dir."""
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    config_path = cfg.data_dir / "config.yaml"

    data = {}
    for section in ("agent", "web", "telegram", "notifications", "paths"):
        data[section] = _dataclass_to_dict(getattr(cfg, section))

    with open(config_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
