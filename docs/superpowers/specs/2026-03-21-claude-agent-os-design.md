# Claude Agent OS — Design Spec

**Date:** 2026-03-21
**Status:** Draft
**Repo:** travis-burmaster/claude-telegram-agent (to be renamed claude-agent-os)

## Overview

Transform the existing claude-telegram-agent (a lightweight Claude Code + Telegram wrapper) into **claude-agent-os**: an always-on, personal AI agent platform for developers. Runs as a macOS LaunchDaemon that survives reboots without login. Provides persistent memory, scheduled tasks, a local web UI, task tracking, and sub-agent spawning.

## Target User

Individual developers who want a personal always-on Claude agent they can interact with via Telegram and a local web dashboard. Open source, self-hosted.

## Architecture

```
┌─────────────────────────────────────┐
│  macOS LaunchDaemon (boot service)  │
│                                     │
│  ┌─────────────────────────────┐    │
│  │  Python Sidecar (FastAPI)   │    │
│  │                             │    │
│  │  ├── Web UI (local only)    │    │
│  │  ├── Cron Scheduler         │    │
│  │  ├── Task Tracker           │    │
│  │  ├── Memory Manager         │    │
│  │  ├── Telegram Bot Listener  │    │
│  │  └── Agent Spawner          │    │
│  └─────────────────────────────┘    │
│              │                      │
│      spawns Claude Code CLI         │
│      sessions as workers            │
│              │                      │
│  ┌───────────┼───────────┐          │
│  ▼           ▼           ▼          │
│ [Agent 1] [Agent 2] [Agent N]       │
│ (cron job) (telegram) (sub-task)    │
└─────────────────────────────────────┘
```

The Python sidecar is the always-on process. Claude Code is stateless — spawned on demand for each conversation, cron job, or sub-task. The sidecar injects soul.md + relevant memories into each Claude session.

### Data Directory

```
~/.claude-agent-os/
  ├── soul.md              # personality/identity definition
  ├── config.yaml          # master configuration
  ├── memory/              # file-based memories (markdown + frontmatter)
  │   ├── index.json       # manifest with metadata
  │   ├── user/            # user preferences and profile
  │   ├── project/         # ongoing work context
  │   ├── feedback/        # corrections and validated approaches
  │   ├── reference/       # pointers to external systems
  │   └── conversation/    # key takeaways from past sessions
  ├── tasks/               # task state
  │   ├── active.json      # current tasks
  │   ├── archive/         # completed tasks by date
  │   └── templates/       # reusable task templates
  ├── cron/                # cron job definitions (YAML)
  ├── logs/                # agent session transcripts
  └── web/                 # web UI static assets
```

## Components

### 1. Soul System (soul.md)

A markdown file at `~/.claude-agent-os/soul.md` that defines the agent's personality, tone, rules, and identity. Injected into every Claude Code session as a system prompt prefix.

Contents include:
- Agent identity and tone
- Behavioral rules (e.g., "never push to main without asking")
- Notification preferences
- Domain knowledge hints

Editable via: direct file editing, web UI (with live preview), or Telegram ("update your soul to be more concise").

### 2. Memory System (File-Based)

Each memory is a markdown file with YAML frontmatter:

```markdown
---
name: user-employer
type: user
tags: [work, identity]
created: 2026-03-21T08:00:00Z
updated: 2026-03-21T08:00:00Z
---
Travis works at Next Link Labs (not Northramp).
```

**Types:** user, project, feedback, reference, conversation

**index.json** serves as a fast-lookup manifest with all memory metadata (name, type, tags, path, timestamps). Rebuilt on startup by scanning the memory directory.

**Memory selection:** When spawning a Claude session, the sidecar selects relevant memories based on:
- Task context keywords matched against memory tags and content
- Memory type relevance to the task
- Recency weighting

**Operations via web UI:** browse, search (full-text + tags), create, edit, delete
**Operations via Telegram:** "remember that...", "forget about...", "what do you know about..."

### 3. Cron System

**Job definitions** are YAML files in `~/.claude-agent-os/cron/`:

```yaml
name: check-deploys
schedule: "*/30 * * * *"
prompt: "Check GitHub Actions status for all my repos. Notify me via Telegram if anything failed."
workspace: ~/git
model: claude-sonnet-4-6
enabled: true
notify: telegram
timeout: 300
```

**Scheduler:** APScheduler running inside the FastAPI sidecar process. Reads job definitions on startup and watches for file changes.

**On trigger:**
1. Spawns a Claude Code subprocess with the job's prompt
2. Injects soul.md + relevant memories
3. Sets working directory to the job's workspace
4. Captures output, enforces timeout
5. Logs result to `~/.claude-agent-os/logs/`
6. Sends notification via configured channel (Telegram)

**Webhooks:** The sidecar exposes `POST /api/webhook/{job-name}` (password-authenticated) for triggering jobs externally from GitHub Actions, scripts, or other services.

**Management:**
- Web UI: create, edit, enable/disable, view run history with logs
- Telegram: "list crons", "disable check-deploys", "run check-deploys now"
- CLI: `claude-agent cron list`, `claude-agent cron run <name>`

### 4. Task Tracker

**Storage:** JSON in `~/.claude-agent-os/tasks/active.json`

**Task schema:**
```json
{
  "id": "t-20260321-001",
  "title": "Fix auth bug in hr-reviews",
  "description": "Richard getting 403 on manage users",
  "status": "in_progress",
  "priority": "high",
  "assignee": "agent",
  "created": "2026-03-21T08:00:00Z",
  "due": "2026-03-21T17:00:00Z",
  "workspace": "~/git/northramp-success-planning",
  "parent": null,
  "subtasks": ["t-20260321-002"],
  "agent_session": "session-abc123",
  "result": null,
  "tags": ["northramp", "bug"]
}
```

**Statuses:** pending → in_progress → completed / failed / blocked

**Behavior:**
- Tasks created via Telegram, web UI, or auto-created by cron jobs
- Agent can autonomously pick up pending tasks (if enabled in config)
- Sub-agents report results back to parent tasks
- Completed tasks auto-archive after 7 days
- Web UI displays a kanban-style board

### 5. Sub-Agent Spawner

When the main agent or a cron job needs to parallelize work:

1. Sidecar builds a temporary CLAUDE.md for the sub-agent containing: soul.md excerpt, relevant memories, task context, and skill instructions
2. Spawns `claude --print --dangerously-skip-permissions -p "<prompt>"` as a subprocess
3. Captures stdout, monitors for timeout
4. On completion: updates the task, logs the session, notifies parent or Telegram
5. Max concurrent agents: configurable (default: 3)

**Guardrails:**
- Each sub-agent runs in a specified workspace directory
- Configurable timeout kills runaway agents
- All sessions logged with full transcript
- Main agent can check on / cancel sub-agents via Telegram or web UI

### 6. Telegram Integration

Replaces the current approach (Claude Code plugin) with a direct Bot API listener in the sidecar:

- **python-telegram-bot** library listens for incoming messages
- On message: spawns a Claude Code session with the user's message as prompt
- Injects soul.md + relevant memories + conversation history
- Streams response back to Telegram
- Supports photo/file attachments (saved to inbox, passed to Claude)
- Access control: allowlist by Telegram user ID (from config.yaml)

### 7. Web UI

**Stack:** FastAPI backend serving vanilla HTML/JS (no build step)

**Security:**
- Binds to 127.0.0.1 by default (configurable to LAN subnet)
- Password authentication with session cookies
- Password set in config.yaml (hashed)

**Pages:**
| Page | Purpose |
|------|---------|
| Dashboard | Agent status, active tasks, recent cron runs, memory count |
| Chat | Send prompts, see responses (spawns Claude session) |
| Tasks | Kanban board — create, edit, archive tasks |
| Cron | Job list, run history, create/edit, enable/disable |
| Memory | Browse, search, edit, delete memories |
| Soul | Edit soul.md with live preview |
| Logs | Browse agent session transcripts |
| Settings | config.yaml editor, password change, model defaults |

### 8. LaunchDaemon (macOS)

A plist file installed to `/Library/LaunchDaemons/com.claude-agent-os.plist`:

```xml
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.claude-agent-os</string>
  <key>ProgramArguments</key>
  <array>
    <string>/path/to/python</string>
    <string>-m</string>
    <string>claude_agent_os.server</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>UserName</key>
  <string>travis</string>
  <key>WorkingDirectory</key>
  <string>/Users/travis</string>
  <key>StandardOutPath</key>
  <string>/Users/travis/.claude-agent-os/logs/daemon-stdout.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/travis/.claude-agent-os/logs/daemon-stderr.log</string>
</dict>
</plist>
```

**CLI installer:** `claude-agent install-daemon` handles plist creation, permission setup, and `launchctl load`.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| Web framework | FastAPI + Uvicorn |
| Scheduler | APScheduler |
| Telegram | python-telegram-bot |
| Frontend | Vanilla HTML/JS/CSS (no build step) |
| Package manager | uv |
| AI runtime | Claude Code CLI (spawned as subprocess) |
| Persistence | Files (markdown, JSON, YAML) |
| Auth | Password + session cookie (web), allowlist (Telegram) |

## Config (config.yaml)

```yaml
agent:
  name: "Claude Agent OS"
  model: "claude-sonnet-4-6"
  max_concurrent_agents: 3
  auto_pickup_tasks: false

web:
  host: "127.0.0.1"
  port: 8420
  password_hash: "<bcrypt hash>"

telegram:
  bot_token: "<from .env>"
  allowed_users: ["8167893346"]

notifications:
  default_channel: "telegram"

paths:
  soul: "~/.claude-agent-os/soul.md"
  memory: "~/.claude-agent-os/memory"
  tasks: "~/.claude-agent-os/tasks"
  cron: "~/.claude-agent-os/cron"
  logs: "~/.claude-agent-os/logs"
```

## Migration from claude-telegram-agent

1. Rename package from `claude_telegram` to `claude_agent_os`
2. Existing CLI commands (`setup`, `launch`, `doctor`, `info`) preserved and extended
3. New commands: `cron`, `task`, `memory`, `install-daemon`
4. Existing .env token config migrated to config.yaml
5. README rewritten for new scope

## Out of Scope (v1)

- Multi-user support (single developer only)
- Cloud deployment (local macOS only for v1)
- Event-based triggers beyond webhooks
- Voice/audio input
- Mobile app (Telegram is the mobile interface)
