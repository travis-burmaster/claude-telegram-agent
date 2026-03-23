# Data Handling Policy

## Data Classification

| Category | Examples | Storage | Encryption |
|---|---|---|---|
| Secrets | Bot tokens, API keys, password hashes | `config.yaml` (gitignored) | At rest via OS keychain (recommended) |
| User messages | Telegram messages, web chat | In-memory during session; logs on disk | Filesystem permissions |
| Memory records | User/feedback/project/reference memories | `~/.claude-agent-os/memory/` | Filesystem permissions |
| Task data | Active and archived tasks | `~/.claude-agent-os/tasks/` | Filesystem permissions |
| Agent logs | Stdout/stderr from agent runs | `~/.claude-agent-os/logs/` | Filesystem permissions |

## Data Flow

1. **Inbound** — Messages arrive via Telegram Bot API (TLS) or localhost web UI (HTTP, localhost-only).
2. **Processing** — Claude Code subprocess processes the message with access to the agent's data directory.
3. **Storage** — Memories, tasks, and logs written to the local filesystem.
4. **Outbound** — Responses sent via Telegram Bot API (TLS) or rendered in the web UI.

## Retention

- Memory records: retained indefinitely unless manually deleted or cleaned per retention policy.
- Logs: retained per `compliance.recordkeeping.retention_period` in `agent.yaml`.
- Task archives: retained indefinitely.

## Access Control

- **Telegram**: Allowlist of user IDs in `config.yaml`. Unauthorized senders are silently ignored.
- **Web UI**: Password-protected via bcrypt hash. Localhost-only by default.
- **Filesystem**: Standard Unix permissions. Data directory owned by the running user.

## Third-Party Data Sharing

This agent sends user messages to the Anthropic API for processing. No other third-party services receive user data unless the user explicitly configures integrations.
