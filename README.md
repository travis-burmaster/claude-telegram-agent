# Claude Telegram Agent

Talk to Claude from your phone. One command, full Claude Code — right in Telegram.

## 30-Second Setup

### 1. Get a bot token

Open Telegram, message [@BotFather](https://t.me/BotFather), type `/newbot`, and follow the prompts. Copy the token it gives you.

### 2. Install & launch

```bash
# Install dependencies (one-time)
npm install -g @anthropic-ai/claude-code
pip install uv
curl -fsSL https://bun.sh/install | bash

# Clone and run
git clone https://github.com/travis-burmaster/claude-telegram-agent
cd claude-telegram-agent
uv sync

# Interactive setup — paste your bot token when prompted
uv run claude-telegram setup

# Go
uv run claude-telegram launch
```

### 3. Pair your phone

DM your bot on Telegram. It will reply with a **6-character code**. Back in your terminal, type:

```
/telegram:access pair <code>
```

That's it. You're connected. Message your bot and Claude responds.

---

## What is this?

This gives you **full Claude Code access from Telegram** — your phone, tablet, desktop app, anywhere Telegram runs. It's not a watered-down chatbot. It's the real thing: Claude can read your files, write code, run commands, search the web, send emails — whatever tools and MCP servers you have configured.

```
You (Telegram): "check the deploy status and fix any failing tests"
Claude: *actually does it, replies in Telegram when done*
```

### How it works

```
Your phone (Telegram) → Telegram Bot API → Claude Code → Your codebase
```

The [official Anthropic Telegram plugin](https://github.com/anthropics/claude-plugins-official) runs as an MCP server inside Claude Code. This repo is a lightweight wrapper that handles setup, token validation, and launching Claude with the right flags.

---

## Commands

| Command | What it does |
|---|---|
| `uv run claude-telegram setup` | Interactive setup — validates your bot token and configures everything |
| `uv run claude-telegram launch` | Starts Claude Code with Telegram connected |
| `uv run claude-telegram doctor` | Checks all dependencies and config |
| `uv run claude-telegram info` | Shows available tools and access policies |

### Launch options

```bash
# Basic launch
uv run claude-telegram launch

# Use a specific model
uv run claude-telegram launch --model claude-opus-4-6

# Point Claude at a specific project
uv run claude-telegram launch --cwd ~/projects/my-app

# Preview the command without running it
uv run claude-telegram launch --dry

# Pass extra flags through to Claude
uv run claude-telegram launch -- --verbose
```

---

## Configuration

Create a `.env` file (or run `setup` to do it interactively):

```bash
cp .env.example .env
```

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Yes | From @BotFather |
| `ANTHROPIC_API_KEY` | No | Claude will prompt if missing |
| `CLAUDE_MODEL` | No | Override the default model |
| `CLAUDE_WORKSPACE` | No | Set Claude's working directory |

---

## Security & Access Control

By default, anyone who finds your bot can try to message it. Lock it down:

```
/telegram:access policy allowlist
```

| Policy | Who can talk to your bot |
|---|---|
| `pairing` | Anyone with a 6-char code you approve (default) |
| `allowlist` | Only specific Telegram user IDs you've added |
| `open` | Anyone (not recommended) |

Get your Telegram user ID from [@userinfobot](https://t.me/userinfobot).

---

## Sending Photos & Files

You can send images to Claude through Telegram. For best quality, long-press the image and choose **Send as File** — this avoids Telegram's compression. Photos are saved to `~/.claude/channels/telegram/inbox/`.

---

## Prerequisites

| Tool | Install | Why |
|---|---|---|
| **Claude Code** | `npm install -g @anthropic-ai/claude-code` | The AI that does the work |
| **Bun** | `curl -fsSL https://bun.sh/install \| bash` | Runs the Telegram plugin |
| **uv** | `pip install uv` | Python package manager for this wrapper |
| **Telegram bot token** | [@BotFather](https://t.me/BotFather) | Your bot's identity |

---

## Troubleshooting

**"command not found: claude"** — Install Claude Code: `npm install -g @anthropic-ai/claude-code`

**"command not found: bun"** — Install Bun: `curl -fsSL https://bun.sh/install | bash`, then restart your terminal

**Bot doesn't respond** — Make sure you've paired (`/telegram:access pair <code>`) and that your access policy allows your user ID

**Run the doctor** — `uv run claude-telegram doctor` checks everything and tells you what's missing

---

## Links

- [Official Telegram Plugin](https://github.com/anthropics/claude-plugins-official)
- [Claude Code Docs](https://docs.anthropic.com/en/docs/claude-code)
- [Setup Guide (dev.to)](https://dev.to/czmilo/claude-code-telegram-plugin-complete-setup-guide-2026-3j0p)

---

MIT License
