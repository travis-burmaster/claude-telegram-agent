"""Conversation log — SQLite-backed record of CLI session interactions."""

from __future__ import annotations

import sqlite3
from pathlib import Path

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS conversation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
    role TEXT NOT NULL,
    content TEXT,
    session_id TEXT
);
"""


def init_conversation_db(db_path: Path | str) -> None:
    """Create the conversation table if it doesn't exist."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_SCHEMA)
    conn.close()


def get_recent_context(db_path: Path | str, limit: int = 50, max_chars: int = 4000) -> str:
    """Return formatted recent conversation entries for injection into agent prompts.

    Also compacts the DB by removing rows beyond the most recent 200.
    """
    db_path = Path(db_path)
    if not db_path.exists():
        return ""

    conn = sqlite3.connect(str(db_path))

    # Compact: keep only last 200 rows
    conn.execute(
        "DELETE FROM conversation WHERE id NOT IN "
        "(SELECT id FROM conversation ORDER BY id DESC LIMIT 200)"
    )
    conn.commit()

    rows = conn.execute(
        "SELECT ts, role, content FROM conversation ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()

    if not rows:
        return ""

    lines = []
    for ts, role, content in reversed(rows):
        label = "User" if role == "user" else "Assistant"
        lines.append(f"[{ts}] **{label}:** {content}")

    text = "\n".join(lines)
    if len(text) > max_chars:
        text = "...(truncated)\n" + text[-max_chars:]

    return text
