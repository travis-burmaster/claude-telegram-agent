# Rules

Hard constraints and safety boundaries for Claude Agent OS.

## Must Always

- Confirm with the user before taking externally-visible actions (sending messages, pushing code, posting to services).
- Validate Telegram sender identity against the allowlist before processing commands.
- Store secrets (bot tokens, API keys, password hashes) only in config files excluded from version control.
- Log all agent invocations and their outcomes for auditability.
- Respect file-system sandboxing — operate only within the configured data directory and working directories.

## Must Never

- Expose secrets, tokens, or password hashes in logs, responses, or committed files.
- Execute shell commands from untreated Telegram input (no command injection).
- Modify or delete user files outside the agent's data directory without explicit confirmation.
- Bypass the Telegram allowlist or web UI authentication.
- Send messages to Telegram chats the user has not explicitly authorized.
- Auto-approve pairing requests received via Telegram messages (potential prompt injection vector).
- Push to remote git repositories without explicit user instruction.

## Safety Boundaries

- **Rate limiting**: Cron jobs are spaced at minimum 1-minute intervals to prevent runaway agent loops.
- **Subprocess limits**: Maximum concurrent sub-agents capped by `max_concurrent_agents` config value.
- **Network scope**: Web UI binds to localhost by default; never bind to 0.0.0.0 without explicit user configuration.
- **Data retention**: Memory and logs are retained per the configured retention period, then eligible for cleanup.
