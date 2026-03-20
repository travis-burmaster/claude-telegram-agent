"""Setup helpers — install plugin, validate bot token, check access control."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import httpx
from rich.console import Console
from rich.panel import Panel

from claude_telegram.config import TELEGRAM_PLUGIN, write_token_to_claude_env

console = Console()


def validate_bot_token(token: str) -> dict | None:
    """Call Telegram getMe to validate the bot token. Returns bot info or None."""
    try:
        r = httpx.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        data = r.json()
        if data.get("ok"):
            return data["result"]
        return None
    except Exception:
        return None


def install_plugin() -> bool:
    """
    Run the Claude Code plugin install command.
    This must run inside an active Claude Code session.
    Returns True if the command likely succeeded.
    """
    console.print("\n[bold yellow]Installing Telegram plugin...[/bold yellow]")
    console.print(f"[dim]Plugin: {TELEGRAM_PLUGIN}[/dim]\n")

    console.print(Panel(
        f"[bold]Run these commands inside your Claude Code session:[/bold]\n\n"
        f"[cyan]/plugin install {TELEGRAM_PLUGIN}[/cyan]\n"
        f"[cyan]/reload-plugins[/cyan]\n\n"
        "Then restart Claude with:\n"
        f"[cyan]claude --channels plugin:{TELEGRAM_PLUGIN}[/cyan]",
        title="Plugin Installation",
        border_style="yellow",
    ))
    return True


def configure_token(token: str) -> bool:
    """Write bot token to Claude's channel env."""
    bot_info = validate_bot_token(token)
    if not bot_info:
        console.print("[red]❌ Invalid bot token — Telegram rejected it.[/red]")
        console.print("[dim]Get a token from @BotFather on Telegram.[/dim]")
        return False

    write_token_to_claude_env(token)
    console.print(f"[green]✅ Token validated and saved![/green]")
    console.print(f"   Bot: [bold]@{bot_info.get('username')}[/bold] ({bot_info.get('first_name')})")
    return True


def build_claude_command(
    model: str | None = None,
    extra_args: list[str] | None = None,
    skip_permissions: bool = True,
) -> list[str]:
    """Build the full claude CLI command with the Telegram channel flag."""
    cmd = ["claude", "--channels", f"plugin:{TELEGRAM_PLUGIN}"]

    if skip_permissions:
        cmd.append("--dangerously-skip-permissions")

    if model:
        cmd += ["--model", model]

    if extra_args:
        cmd += extra_args

    return cmd


def launch_claude(
    workspace: str | None = None,
    model: str | None = None,
    extra_args: list[str] | None = None,
    skip_permissions: bool = True,
    dry_run: bool = False,
) -> int:
    """Exec into Claude Code with the Telegram plugin. Replaces current process."""
    import os
    from pathlib import Path

    cmd = build_claude_command(model=model, extra_args=extra_args, skip_permissions=skip_permissions)

    display_parts = " ".join(cmd)
    if workspace:
        display_parts += f"\n(working directory: {workspace})"

    console.print(Panel(
        f"[bold green]Launching Claude Code + Telegram[/bold green]\n\n"
        + display_parts,
        border_style="green",
    ))

    if dry_run:
        console.print("[yellow]Dry run — not executing.[/yellow]")
        return 0

    # Change to workspace directory before exec
    if workspace:
        ws_path = Path(workspace).expanduser().resolve()
        os.chdir(ws_path)

    # Replace current process with claude
    try:
        os.execvp(cmd[0], cmd)
    except FileNotFoundError:
        console.print("[red]❌ 'claude' not found in PATH.[/red]")
        console.print("[dim]Install Claude Code: npm install -g @anthropic-ai/claude-code[/dim]")
        return 1

    return 0  # unreachable but satisfies type checker
