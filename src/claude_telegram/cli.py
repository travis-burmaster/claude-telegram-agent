"""claude-telegram CLI — one command to spin up Claude Code + Telegram plugin."""

from __future__ import annotations

import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from claude_telegram import __version__
from claude_telegram.config import check_dependencies, load_config
from claude_telegram.setup import configure_token, install_plugin, launch_claude

console = Console()

BANNER = f"""
[bold cyan]claude-telegram[/bold cyan] [dim]v{__version__}[/dim]
[dim]Claude Code + Telegram plugin wrapper[/dim]
"""


@click.group(invoke_without_command=True)
@click.version_option(__version__, prog_name="claude-telegram")
@click.pass_context
def main(ctx: click.Context):
    """Spin up Claude Code with the official Telegram plugin.

    \b
    Quick start:
      claude-telegram setup          Check deps + configure bot token
      claude-telegram launch         Start Claude Code with Telegram enabled
      claude-telegram launch --dry   Preview the command without running

    \b
    One-liner (after setup):
      claude-telegram launch
    """
    if ctx.invoked_subcommand is None:
        console.print(BANNER)
        click.echo(ctx.get_help())


# ── doctor ────────────────────────────────────────────────────────────────────

@main.command()
def doctor():
    """Check that all required tools are installed."""
    console.print(BANNER)
    deps = check_dependencies()
    cfg = load_config()

    table = Table(title="Dependency Check", show_header=True, header_style="bold cyan")
    table.add_column("Tool", style="bold")
    table.add_column("Status")
    table.add_column("Notes")

    statuses = {
        "claude": ("✅ found", "") if deps["claude"] else (
            "❌ missing", "npm install -g @anthropic-ai/claude-code"
        ),
        "bun": ("✅ found", "") if deps["bun"] else (
            "⚠️  missing", "curl -fsSL https://bun.sh/install | bash  (needed by plugin)"
        ),
        "npx": ("✅ found", "") if deps["npx"] else (
            "⚠️  missing", "Install Node.js from nodejs.org"
        ),
    }

    for tool, (status, note) in statuses.items():
        table.add_row(tool, status, note)

    console.print(table)

    # Config check
    console.print()
    token = cfg["telegram_bot_token"]
    api_key = cfg["anthropic_api_key"]

    console.print("[bold]Configuration:[/bold]")
    console.print(f"  TELEGRAM_BOT_TOKEN : {'✅ set' if token else '❌ not set (run setup)'}")
    console.print(f"  ANTHROPIC_API_KEY  : {'✅ set' if api_key else '⚠️  not set (Claude will prompt)'}")
    console.print(f"  CLAUDE_MODEL       : {cfg['claude_model'] or '(default)'}")
    console.print(f"  CLAUDE_WORKSPACE   : {cfg['workspace']}")

    all_ok = deps["claude"] and bool(token)
    if all_ok:
        console.print("\n[green]✅ Ready to launch! Run: claude-telegram launch[/green]")
    else:
        console.print("\n[yellow]⚠️  Some setup required. Run: claude-telegram setup[/yellow]")


# ── setup ─────────────────────────────────────────────────────────────────────

@main.command()
@click.option("--token", "-t", envvar="TELEGRAM_BOT_TOKEN", help="Telegram bot token from @BotFather")
@click.option("--skip-install", is_flag=True, help="Skip plugin install instructions")
def setup(token: str | None, skip_install: bool):
    """Interactive setup: validate bot token + configure Claude plugin.

    \b
    Steps performed:
      1. Check dependencies (claude, bun)
      2. Validate and save your Telegram bot token
      3. Show plugin install instructions
    """
    console.print(BANNER)

    # 1. Check deps
    deps = check_dependencies()
    if not deps["claude"]:
        console.print("[red]❌ 'claude' not found. Install Claude Code first:[/red]")
        console.print("   npm install -g @anthropic-ai/claude-code")
        sys.exit(1)

    if not deps["bun"]:
        console.print("[yellow]⚠️  'bun' not found. The Telegram plugin requires Bun:[/yellow]")
        console.print("   curl -fsSL https://bun.sh/install | bash")
        console.print()

    # 2. Token
    if not token:
        console.print(Panel(
            "Create a bot at [link=https://t.me/BotFather]@BotFather[/link] on Telegram\n"
            "and paste the token below.\n\n"
            "[dim]The token looks like: 123456789:AAHfiqksKZ8...[/dim]",
            title="Telegram Bot Token",
            border_style="cyan",
        ))
        token = click.prompt("Bot token", hide_input=True)

    if not configure_token(token):
        sys.exit(1)

    # 3. Plugin install guide
    if not skip_install:
        install_plugin()

    console.print(Panel(
        "[bold green]Setup complete![/bold green]\n\n"
        "Next steps:\n"
        "1. Open Claude Code: [cyan]claude[/cyan]\n"
        "2. Install plugin: [cyan]/plugin install telegram@claude-plugins-official[/cyan]\n"
        "3. Reload: [cyan]/reload-plugins[/cyan]\n"
        "4. Exit and run: [cyan]claude-telegram launch[/cyan]\n"
        "5. DM your bot on Telegram to get the pairing code\n"
        "6. In Claude: [cyan]/telegram:access pair <code>[/cyan]\n"
        "7. Lock down: [cyan]/telegram:access policy allowlist[/cyan]",
        title="✅ You're Ready",
        border_style="green",
    ))


# ── launch ────────────────────────────────────────────────────────────────────

@main.command()
@click.option("--workspace", "-w", envvar="CLAUDE_WORKSPACE", help="Working directory for Claude")
@click.option("--model", "-m", envvar="CLAUDE_MODEL", help="Claude model to use (e.g. claude-opus-4-5)")
@click.option("--dry", is_flag=True, help="Print command without running it")
@click.option(
    "--skip-permissions/--no-skip-permissions",
    default=True,
    show_default=True,
    help="Pass --dangerously-skip-permissions to Claude (enabled by default for Telegram use)",
)
@click.argument("extra_args", nargs=-1, type=click.UNPROCESSED)
def launch(workspace: str | None, model: str | None, dry: bool, skip_permissions: bool, extra_args: tuple):
    """Start Claude Code with the Telegram plugin enabled.

    \b
    Runs:
      claude --channels plugin:telegram@claude-plugins-official
             --dangerously-skip-permissions [options]

    \b
    --dangerously-skip-permissions is ON by default so Claude can act autonomously
    over Telegram without interactive approval prompts. Disable with --no-skip-permissions.

    \b
    Examples:
      claude-telegram launch
      claude-telegram launch --model claude-opus-4-5
      claude-telegram launch --cwd ~/projects/myapp
      claude-telegram launch --no-skip-permissions
      claude-telegram launch --dry
    """
    console.print(BANNER)

    cfg = load_config()
    deps = check_dependencies()

    # Pre-flight checks
    if not deps["claude"]:
        console.print("[red]❌ 'claude' not found. Run: npm install -g @anthropic-ai/claude-code[/red]")
        sys.exit(1)

    if not cfg["telegram_bot_token"]:
        console.print("[red]❌ TELEGRAM_BOT_TOKEN not set. Run: claude-telegram setup[/red]")
        sys.exit(1)

    if skip_permissions:
        console.print("[yellow]⚠️  --dangerously-skip-permissions is enabled (use --no-skip-permissions to disable)[/yellow]")

    # Use config defaults if not passed
    ws = workspace or cfg["workspace"] or None
    mdl = model or cfg["claude_model"] or None

    exit_code = launch_claude(
        workspace=ws,
        model=mdl,
        extra_args=list(extra_args) if extra_args else None,
        skip_permissions=skip_permissions,
        dry_run=dry,
    )
    sys.exit(exit_code)


# ── info ──────────────────────────────────────────────────────────────────────

@main.command()
def info():
    """Show plugin info and useful Telegram commands."""
    console.print(BANNER)
    console.print(Panel(
        "[bold]Claude Code Telegram Plugin[/bold]\n"
        "Official plugin by Anthropic\n"
        "Repository: [link=https://github.com/anthropics/claude-plugins-official]"
        "claude-plugins-official[/link]\n\n"

        "[bold]MCP Tools exposed to Claude:[/bold]\n"
        "  reply         — Send message (text, files, images up to 50MB)\n"
        "  react         — Add emoji reaction (👍 👎 ❤ 🔥 👀 etc.)\n"
        "  edit_message  — Edit a previously sent bot message\n\n"

        "[bold]Useful Claude Code commands:[/bold]\n"
        "  /plugin install telegram@claude-plugins-official\n"
        "  /reload-plugins\n"
        "  /telegram:configure <BOT_TOKEN>\n"
        "  /telegram:access pair <code>\n"
        "  /telegram:access policy allowlist\n"
        "  /telegram:access policy pairing\n\n"

        "[bold]Inbound photos:[/bold]\n"
        "  Saved to ~/.claude/channels/telegram/inbox/\n"
        "  Send as document for uncompressed original\n\n"

        "[bold]Access policies:[/bold]\n"
        "  pairing    — users pair with 6-char code (default)\n"
        "  allowlist  — only approved user IDs can interact\n"
        "  open       — anyone can message (not recommended)\n\n"

        "[dim]Get your Telegram user ID from @userinfobot[/dim]",
        title="Plugin Reference",
        border_style="cyan",
    ))
