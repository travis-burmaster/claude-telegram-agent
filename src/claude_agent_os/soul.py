"""Soul system — the agent's personality and instruction set."""

from pathlib import Path

DEFAULT_SOUL = """# Soul

You are a personal AI agent running as an always-on background service.
You help your user by completing tasks, managing information, and staying
proactive about their needs.

## Core Principles
- Be concise and action-oriented
- Ask for clarification only when truly needed
- Maintain context across conversations
- Respect the user's time and attention
"""


def load_soul(soul_path: Path) -> str:
    """Load soul content from file, returning DEFAULT_SOUL if not found."""
    if soul_path.exists():
        return soul_path.read_text()
    return DEFAULT_SOUL


def save_soul(soul_path: Path, content: str) -> None:
    """Write soul content to file, creating parent dirs if needed."""
    soul_path.parent.mkdir(parents=True, exist_ok=True)
    soul_path.write_text(content)
