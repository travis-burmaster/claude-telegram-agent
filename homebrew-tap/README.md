# homebrew-claude-agent-os

Homebrew tap for [claude-agent-os](https://github.com/travis-burmaster/claude-telegram-agent) — an always-on personal AI agent with memory, tasks, cron jobs, and a web dashboard.

## Install

```bash
brew tap travis-burmaster/claude-agent-os
brew install claude-agent-os
```

## First-time setup

```bash
# Create data directory and set your web dashboard password
claude-agent setup

# Start as a background service (auto-restarts on login)
brew services start claude-agent-os

# Or run in the foreground
claude-agent server
```

The web dashboard will be at **http://127.0.0.1:8420**.

## Telegram

Add your bot token and allowed user IDs to `~/.claude-agent-os/config.yaml`:

```yaml
telegram:
  bot_token: "YOUR_BOT_TOKEN"
  allowed_users:
    - "YOUR_TELEGRAM_USER_ID"
```

Then restart the service: `brew services restart claude-agent-os`

## Useful commands

| Command | Description |
|---|---|
| `claude-agent server` | Start server in foreground |
| `claude-agent doctor` | Check dependencies and config |
| `claude-agent setup` | Interactive first-time setup |
| `claude-agent task list` | List tasks |
| `claude-agent memory list` | List memories |
| `claude-agent cron list` | List scheduled jobs |
| `brew services start claude-agent-os` | Run as background service |
| `brew services stop claude-agent-os` | Stop background service |

## Updating

```bash
brew update && brew upgrade claude-agent-os
```
