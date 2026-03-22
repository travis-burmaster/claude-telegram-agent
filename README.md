# Claude Agent OS

Always-on personal AI agent for developers. Memory, scheduled tasks, web dashboard, sub-agents -- all from your terminal or Telegram.

## Quick Start (macOS — Homebrew)

```bash
# 1. Install via Homebrew
brew tap travis-burmaster/claude-telegram-agent
brew install --HEAD claude-agent-os

# 2. Run setup (creates data dirs, sets web password)
claude-agent setup

# 3. Start as a background service (survives reboots)
brew services start claude-agent-os

# 4. Open the web UI
open http://127.0.0.1:8420
```

To connect Telegram, add your bot token and allowed user IDs to `~/.claude-agent-os/config.yaml` (see Configuration below), then restart the service with `brew services restart claude-agent-os`.

## Quick Start (from source)

```bash
# 1. Clone and install
git clone https://github.com/travis-burmaster/claude-telegram-agent
cd claude-telegram-agent
uv sync

# 2. Run setup (creates data dirs, sets web password)
uv run claude-agent setup

# 3. Start the server
uv run claude-agent server

# 4. Open the web UI
open http://127.0.0.1:8420
```

To connect Telegram, add your bot token and allowed user IDs to `~/.claude-agent-os/config.yaml` (see Configuration below), then restart.

## Features

- **Soul system** -- Define your agent's personality and instructions in `soul.md`
- **Persistent memory** -- File-based memories with YAML frontmatter, search, and tagging
- **Task tracker** -- Kanban-style task management with priorities and archival
- **Cron jobs** -- Scheduled Claude agent runs from YAML definitions
- **Webhooks** -- Trigger agent runs via HTTP POST
- **Sub-agent spawning** -- Pool-based concurrent Claude subprocess management
- **Local web UI** -- Password-protected dashboard with chat, tasks, memory, cron, and settings
- **Telegram integration** -- Message your agent from your phone with user allowlist
- **macOS LaunchDaemon** -- Survives reboots for true always-on operation

## Commands

| Command | Description |
|---|---|
| `claude-agent server` | Start the agent server |
| `claude-agent setup` | Interactive setup (dirs, password, config) |
| `claude-agent doctor` | Check dependencies and configuration |
| `claude-agent cron list` | List all cron jobs |
| `claude-agent cron run <name>` | Trigger a cron job immediately |
| `claude-agent task list` | List tasks (with optional `--status` filter) |
| `claude-agent task create <title>` | Create a new task |
| `claude-agent memory list` | List memories (with optional `--type` filter) |
| `claude-agent memory search <query>` | Search memories |
| `claude-agent install-daemon` | Install macOS LaunchDaemon |
| `claude-agent uninstall-daemon` | Remove the LaunchDaemon |

## Web UI

The web dashboard runs on `http://127.0.0.1:8420` by default (password protected). It includes:

- **Chat** -- Talk to Claude directly from the browser
- **Tasks** -- Kanban board for task management
- **Memory** -- Browse, search, and manage memories
- **Cron** -- View and manage scheduled jobs
- **Logs** -- Live agent output logs
- **Settings** -- Configuration editor

## Configuration

All configuration lives in `~/.claude-agent-os/config.yaml`:

```yaml
agent:
  name: Claude Agent OS
  model: claude-sonnet-4-6
  max_concurrent_agents: 3

web:
  host: 127.0.0.1
  port: 8420
  password_hash: ""  # Set via 'claude-agent setup'

telegram:
  bot_token: ""  # From @BotFather (or set TELEGRAM_BOT_TOKEN env var)
  allowed_users:
    - "123456789"  # Telegram user IDs

paths:
  soul: soul.md
  memory: memory
  tasks: tasks
  cron: cron
  logs: logs
```

Environment variables can override config values:

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Overrides `telegram.bot_token` in config |

## Always-on operation (macOS)

**Homebrew (recommended):**

```bash
brew services start claude-agent-os   # start and enable on boot
brew services restart claude-agent-os # restart after config changes
brew services stop claude-agent-os    # stop the service
```

Logs: `/opt/homebrew/var/log/claude-agent-os.log` and `claude-agent-os-error.log`.

**LaunchDaemon (from-source installs):**

```bash
# Install (requires sudo)
uv run claude-agent install-daemon

# Uninstall
uv run claude-agent uninstall-daemon
```

Logs: `~/.claude-agent-os/logs/daemon-stdout.log`.

## Original Telegram Wrapper

The original `claude-telegram` wrapper is still available for a simpler Telegram-only setup. It launches Claude Code with the official Telegram plugin:

```bash
uv run claude-telegram setup
uv run claude-telegram launch
```

See `src/claude_telegram/` for details.

## License

MIT
