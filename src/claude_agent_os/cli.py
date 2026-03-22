"""CLI entry point for claude-agent-os."""

import logging
import sys

import click
from rich.console import Console
from rich.table import Table

from claude_agent_os import __version__

console = Console()


@click.group(invoke_without_command=True)
@click.version_option(__version__, prog_name="claude-agent-os")
@click.pass_context
def main(ctx):
    """Claude Agent OS -- always-on personal AI agent."""
    if ctx.invoked_subcommand is None:
        console.print(f"[bold cyan]claude-agent-os[/bold cyan] [dim]v{__version__}[/dim]")
        click.echo(ctx.get_help())


@main.command()
@click.option("--host", default=None, help="Bind host (overrides config)")
@click.option("--port", default=None, type=int, help="Bind port (overrides config)")
def server(host, port):
    """Start the agent server."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    from claude_agent_os.server import create_app
    import uvicorn

    app = create_app()
    h = host or app.state.config.web.host
    p = port or app.state.config.web.port
    console.print(f"[green]Starting Claude Agent OS on {h}:{p}[/green]")
    uvicorn.run(app, host=h, port=p)


@main.command()
def doctor():
    """Check dependencies and configuration."""
    import shutil
    from pathlib import Path
    from claude_agent_os.config import DEFAULT_DATA_DIR

    ok = True

    # Python version
    v = sys.version_info
    if v >= (3, 11):
        console.print(f"[green]OK[/green]  Python {v.major}.{v.minor}.{v.micro}")
    else:
        console.print(f"[red]FAIL[/red]  Python {v.major}.{v.minor} (need >= 3.11)")
        ok = False

    # Claude CLI
    if shutil.which("claude"):
        console.print("[green]OK[/green]  claude CLI found")
    else:
        console.print("[red]FAIL[/red]  claude CLI not found — npm install -g @anthropic-ai/claude-code")
        ok = False

    # Data dir
    if DEFAULT_DATA_DIR.exists():
        console.print(f"[green]OK[/green]  Data dir: {DEFAULT_DATA_DIR}")
    else:
        console.print(f"[yellow]WARN[/yellow]  Data dir not found: {DEFAULT_DATA_DIR} (run 'claude-agent setup')")

    # Config file
    config_path = DEFAULT_DATA_DIR / "config.yaml"
    if config_path.exists():
        console.print(f"[green]OK[/green]  Config: {config_path}")
    else:
        console.print(f"[yellow]WARN[/yellow]  No config.yaml (defaults will be used)")

    # Soul file
    soul_path = DEFAULT_DATA_DIR / "soul.md"
    if soul_path.exists():
        console.print(f"[green]OK[/green]  Soul: {soul_path}")
    else:
        console.print(f"[yellow]WARN[/yellow]  No soul.md")

    if ok:
        console.print("\n[bold green]All checks passed.[/bold green]")
    else:
        console.print("\n[bold red]Some checks failed.[/bold red]")
        raise SystemExit(1)


# ── Cron commands ──────────────────────────────────────────────────


@main.group()
def cron():
    """Manage cron jobs."""
    pass


@cron.command("list")
def cron_list():
    """List all cron jobs."""
    from claude_agent_os.config import load_config
    import yaml

    cfg = load_config()
    cron_dir = cfg.paths.cron

    table = Table(title="Cron Jobs")
    table.add_column("Name", style="cyan")
    table.add_column("Schedule", style="green")
    table.add_column("Enabled", style="yellow")

    if not cron_dir.exists():
        console.print("[dim]No cron directory found.[/dim]")
        return

    for f in sorted(cron_dir.glob("*.yaml")):
        with open(f) as fh:
            job = yaml.safe_load(fh) or {}
        table.add_row(
            job.get("name", f.stem),
            job.get("schedule", "?"),
            str(job.get("enabled", True)),
        )

    console.print(table)


@cron.command("run")
@click.argument("name")
def cron_run(name):
    """Trigger a cron job immediately."""
    import asyncio
    from claude_agent_os.config import load_config
    from claude_agent_os.agents import AgentPool
    from claude_agent_os.cron import CronScheduler

    cfg = load_config()
    pool = AgentPool(max_concurrent=cfg.agent.max_concurrent_agents)
    scheduler = CronScheduler(cfg.paths.cron, pool, cfg)

    async def _run():
        await scheduler.run_job(name)

    console.print(f"[cyan]Running cron job: {name}[/cyan]")
    asyncio.run(_run())
    console.print("[green]Done.[/green]")


# ── Task commands ──────────────────────────────────────────────────


@main.group()
def task():
    """Manage tasks."""
    pass


@task.command("list")
@click.option("--status", default=None, help="Filter by status")
def task_list(status):
    """List tasks."""
    from claude_agent_os.config import load_config
    from claude_agent_os.tasks import TaskManager

    cfg = load_config()
    mgr = TaskManager(cfg.paths.tasks)
    tasks = mgr.list(status=status)

    table = Table(title="Tasks")
    table.add_column("ID", style="cyan")
    table.add_column("Title")
    table.add_column("Status", style="yellow")
    table.add_column("Priority", style="magenta")

    for t in tasks:
        table.add_row(t["id"], t["title"], t["status"], t.get("priority", ""))

    console.print(table)


@task.command("create")
@click.argument("title")
@click.option("--priority", default="medium", help="Task priority")
@click.option("--description", default="", help="Task description")
def task_create(title, priority, description):
    """Create a new task."""
    from claude_agent_os.config import load_config
    from claude_agent_os.tasks import TaskManager

    cfg = load_config()
    mgr = TaskManager(cfg.paths.tasks)
    t = mgr.create(title=title, priority=priority, description=description)
    console.print(f"[green]Created task {t['id']}: {t['title']}[/green]")


# ── Memory commands ────────────────────────────────────────────────


@main.group()
def memory():
    """Manage memories."""
    pass


@memory.command("list")
@click.option("--type", "mem_type", default=None, help="Filter by memory type")
def memory_list(mem_type):
    """List memories."""
    from claude_agent_os.config import load_config
    from claude_agent_os.memory import MemoryManager

    cfg = load_config()
    mgr = MemoryManager(cfg.paths.memory)
    memories = mgr.list(mem_type=mem_type)

    table = Table(title="Memories")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Tags", style="yellow")

    for m in memories:
        table.add_row(m["name"], m["type"], ", ".join(m.get("tags", [])))

    console.print(table)


@memory.command("search")
@click.argument("query")
def memory_search(query):
    """Search memories."""
    from claude_agent_os.config import load_config
    from claude_agent_os.memory import MemoryManager

    cfg = load_config()
    mgr = MemoryManager(cfg.paths.memory)
    results = mgr.search(query)

    if not results:
        console.print("[dim]No results found.[/dim]")
        return

    table = Table(title=f"Search: {query}")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Tags", style="yellow")

    for m in results:
        table.add_row(m["name"], m["type"], ", ".join(m.get("tags", [])))

    console.print(table)


# ── Setup and daemon ───────────────────────────────────────────────


@main.command()
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
def setup(password):
    """Interactive setup -- create data dirs, set password, configure."""
    from claude_agent_os.config import DEFAULT_DATA_DIR, load_config, save_config
    from claude_agent_os.auth import hash_password

    console.print(f"[cyan]Setting up Claude Agent OS in {DEFAULT_DATA_DIR}[/cyan]")

    # Create all data directories
    for subdir in ("memory", "tasks", "cron", "logs", "inbox"):
        d = DEFAULT_DATA_DIR / subdir
        d.mkdir(parents=True, exist_ok=True)
        console.print(f"  [dim]Created {d}[/dim]")

    # Write default soul.md if it doesn't exist
    soul_path = DEFAULT_DATA_DIR / "soul.md"
    if not soul_path.exists():
        soul_path.write_text(
            "# Soul\n\n"
            "You are Claude Agent OS, an always-on personal AI agent.\n"
            "Be helpful, precise, and proactive.\n"
        )
        console.print(f"  [dim]Created {soul_path}[/dim]")

    # Set password in config
    cfg = load_config()
    cfg.web.password_hash = hash_password(password)
    save_config(cfg)
    console.print("[green]Password set.[/green]")
    console.print(f"[green]Config saved to {cfg.data_dir / 'config.yaml'}[/green]")
    console.print("\n[bold green]Setup complete![/bold green] Run [cyan]claude-agent server[/cyan] to start.")


@main.command("install-daemon")
def install_daemon():
    """Install macOS LaunchDaemon for always-on operation."""
    import getpass
    import shutil
    from pathlib import Path
    from claude_agent_os.config import DEFAULT_DATA_DIR

    if sys.platform != "darwin":
        console.print("[red]LaunchDaemon is macOS only.[/red]")
        raise SystemExit(1)

    template_path = Path(__file__).parent.parent.parent / "daemon" / "com.claude-agent-os.plist.template"
    if not template_path.exists():
        # Try relative to the installed package
        template_path = Path(__file__).resolve().parent.parent.parent / "daemon" / "com.claude-agent-os.plist.template"

    if not template_path.exists():
        console.print(f"[red]Template not found at {template_path}[/red]")
        raise SystemExit(1)

    username = getpass.getuser()
    home_dir = str(Path.home())
    python_path = sys.executable
    path_env = "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin"
    data_dir = str(DEFAULT_DATA_DIR)

    # Ensure logs dir exists
    (DEFAULT_DATA_DIR / "logs").mkdir(parents=True, exist_ok=True)

    content = template_path.read_text()
    content = content.replace("{{PYTHON_PATH}}", python_path)
    content = content.replace("{{USERNAME}}", username)
    content = content.replace("{{HOME_DIR}}", home_dir)
    content = content.replace("{{PATH}}", path_env)
    content = content.replace("{{DATA_DIR}}", data_dir)

    plist_name = "com.claude-agent-os.plist"
    dest = Path("/Library/LaunchDaemons") / plist_name

    # Write to temp, then copy with sudo
    tmp = Path("/tmp") / plist_name
    tmp.write_text(content)

    console.print(f"[cyan]Installing LaunchDaemon to {dest}[/cyan]")
    console.print("[yellow]You may be prompted for your password (sudo required).[/yellow]")

    import subprocess

    subprocess.run(["sudo", "cp", str(tmp), str(dest)], check=True)
    subprocess.run(["sudo", "launchctl", "load", str(dest)], check=True)
    tmp.unlink(missing_ok=True)

    console.print("[green]LaunchDaemon installed and loaded.[/green]")
    console.print(f"[dim]Logs: {data_dir}/logs/daemon-stdout.log[/dim]")


@main.command("uninstall-daemon")
def uninstall_daemon():
    """Remove the LaunchDaemon."""
    from pathlib import Path
    import subprocess

    if sys.platform != "darwin":
        console.print("[red]LaunchDaemon is macOS only.[/red]")
        raise SystemExit(1)

    plist = Path("/Library/LaunchDaemons/com.claude-agent-os.plist")
    if not plist.exists():
        console.print("[yellow]LaunchDaemon not found — nothing to remove.[/yellow]")
        return

    console.print("[cyan]Removing LaunchDaemon...[/cyan]")
    subprocess.run(["sudo", "launchctl", "unload", str(plist)], check=True)
    subprocess.run(["sudo", "rm", str(plist)], check=True)
    console.print("[green]LaunchDaemon removed.[/green]")


if __name__ == "__main__":
    main()
