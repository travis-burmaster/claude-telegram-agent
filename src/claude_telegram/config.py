"""Configuration management for claude-telegram."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from dotenv import load_dotenv

# ── Paths ──────────────────────────────────────────────────────────────────────
HOME = Path.home()
CLAUDE_DIR = HOME / ".claude"
TELEGRAM_ENV = CLAUDE_DIR / "channels" / "telegram" / ".env"
LOCAL_ENV = Path(".env")

# ── Plugin identifier ─────────────────────────────────────────────────────────
TELEGRAM_PLUGIN = "telegram@claude-plugins-official"
CLAUDE_CHANNEL_FLAG = f"plugin:{TELEGRAM_PLUGIN}"


def load_config() -> dict:
    """Load configuration from .env (local first, then Claude's channel env)."""
    # Local .env takes precedence
    if LOCAL_ENV.exists():
        load_dotenv(LOCAL_ENV, override=False)

    # Fall back to Claude's channel env
    if TELEGRAM_ENV.exists():
        load_dotenv(TELEGRAM_ENV, override=False)

    return {
        "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN", ""),
        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY", ""),
        "claude_model": os.getenv("CLAUDE_MODEL", ""),
        "allowed_user_ids": os.getenv("TELEGRAM_ALLOWED_IDS", ""),
        "workspace": os.getenv("CLAUDE_WORKSPACE", str(Path.cwd())),
    }


def check_dependencies() -> dict[str, bool]:
    """Check that required tools are installed."""
    return {
        "claude": shutil.which("claude") is not None,
        "bun": shutil.which("bun") is not None,
        "npx": shutil.which("npx") is not None,
    }


def write_token_to_claude_env(token: str) -> None:
    """Write TELEGRAM_BOT_TOKEN to Claude's channel env file."""
    TELEGRAM_ENV.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    if TELEGRAM_ENV.exists():
        lines = TELEGRAM_ENV.read_text().splitlines()

    # Replace existing or append
    key = "TELEGRAM_BOT_TOKEN"
    new_line = f"{key}={token}"
    replaced = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = new_line
            replaced = True
            break
    if not replaced:
        lines.append(new_line)

    TELEGRAM_ENV.write_text("\n".join(lines) + "\n")
