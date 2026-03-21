# Claude Agent OS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform claude-telegram-agent into claude-agent-os — an always-on personal AI agent with memory, cron, tasks, web UI, sub-agents, and LaunchDaemon support.

**Architecture:** Python sidecar (FastAPI) runs as a macOS LaunchDaemon. It manages memory, cron, tasks, Telegram, and a local web UI. Claude Code CLI sessions are spawned as stateless workers on demand.

**Tech Stack:** Python 3.11+, FastAPI, Uvicorn, APScheduler, python-telegram-bot, vanilla HTML/JS/CSS, uv

**Spec:** `docs/superpowers/specs/2026-03-21-claude-agent-os-design.md`

---

## File Structure

```
claude-agent-os/
├── pyproject.toml                          # renamed package, new deps
├── LICENSE
├── README.md                              # rewritten for new scope
├── .env.example
├── .gitignore
├── src/claude_agent_os/
│   ├── __init__.py                        # version
│   ├── cli.py                             # click CLI entry point
│   ├── config.py                          # config.yaml + paths
│   ├── server.py                          # FastAPI app + startup
│   ├── auth.py                            # password auth middleware
│   ├── soul.py                            # soul.md loader
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── manager.py                     # CRUD, search, index rebuild
│   │   └── selector.py                    # context-based memory selection
│   ├── tasks/
│   │   ├── __init__.py
│   │   └── manager.py                     # task CRUD, status transitions, archival
│   ├── cron/
│   │   ├── __init__.py
│   │   └── scheduler.py                   # APScheduler wrapper, job loader
│   ├── agents/
│   │   ├── __init__.py
│   │   └── spawner.py                     # Claude Code subprocess management
│   ├── telegram/
│   │   ├── __init__.py
│   │   └── bot.py                         # python-telegram-bot listener
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes_memory.py               # /api/memory/* endpoints
│   │   ├── routes_tasks.py                # /api/tasks/* endpoints
│   │   ├── routes_cron.py                 # /api/cron/* endpoints
│   │   ├── routes_agents.py               # /api/agents/* endpoints
│   │   ├── routes_soul.py                 # /api/soul/* endpoints
│   │   ├── routes_chat.py                 # /api/chat/* endpoints
│   │   ├── routes_logs.py                 # /api/logs/* endpoints
│   │   ├── routes_settings.py             # /api/settings/* endpoints
│   │   └── routes_webhook.py              # /api/webhook/* endpoints
│   └── web/
│       ├── static/
│       │   ├── style.css
│       │   └── app.js
│       └── templates/
│           ├── base.html                  # layout with nav
│           ├── login.html
│           ├── dashboard.html
│           ├── chat.html
│           ├── tasks.html
│           ├── cron.html
│           ├── memory.html
│           ├── soul.html
│           ├── logs.html
│           └── settings.html
├── tests/
│   ├── conftest.py                        # fixtures (tmp data dir, test config)
│   ├── test_config.py
│   ├── test_soul.py
│   ├── test_memory.py
│   ├── test_tasks.py
│   ├── test_cron.py
│   ├── test_spawner.py
│   ├── test_auth.py
│   └── test_api.py
├── daemon/
│   └── com.claude-agent-os.plist.template # LaunchDaemon template
└── docs/
    └── superpowers/
        ├── specs/
        │   └── 2026-03-21-claude-agent-os-design.md
        └── plans/
            └── 2026-03-21-claude-agent-os.md  (this file)
```

---

## Phase 1: Foundation (Package Rename + Config + Soul + Memory)

### Task 1: Rename package and update pyproject.toml

**Files:**
- Modify: `pyproject.toml`
- Rename: `src/claude_telegram/` → `src/claude_agent_os/`
- Modify: `src/claude_agent_os/__init__.py`

- [ ] **Step 1: Rename the source directory**

```bash
mv src/claude_telegram src/claude_agent_os
```

- [ ] **Step 2: Update pyproject.toml**

```toml
[project]
name = "claude-agent-os"
version = "0.2.0"
description = "Always-on personal AI agent with memory, cron, tasks, and web UI"
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
authors = [{ name = "Travis Burmaster", email = "travis@burmaster.com" }]
keywords = ["claude", "claude-code", "telegram", "agent", "mcp", "ai"]

dependencies = [
    "python-dotenv>=1.0.0",
    "click>=8.1.0",
    "rich>=13.0.0",
    "httpx>=0.27.0",
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "apscheduler>=3.10.0",
    "python-telegram-bot>=21.0",
    "pyyaml>=6.0.0",
    "bcrypt>=4.0.0",
    "jinja2>=3.1.0",
    "python-multipart>=0.0.9",
]

[project.scripts]
claude-agent = "claude_agent_os.cli:main"
# Keep old name for backwards compat
claude-telegram = "claude_agent_os.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/claude_agent_os"]
```

- [ ] **Step 3: Update __init__.py**

```python
"""claude-agent-os — always-on personal AI agent platform."""
__version__ = "0.2.0"
```

- [ ] **Step 4: Update internal imports in cli.py, config.py, setup.py**

Replace all `from claude_telegram` with `from claude_agent_os`.

- [ ] **Step 5: Run uv sync to install new deps**

```bash
uv sync
```

- [ ] **Step 6: Verify old CLI still works**

```bash
uv run claude-agent --version
```
Expected: `claude-agent-os, version 0.2.0`

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "refactor: rename package to claude-agent-os, add new dependencies"
```

---

### Task 2: Config system (config.yaml)

**Files:**
- Create: `src/claude_agent_os/config.py` (rewrite)
- Test: `tests/test_config.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create test fixtures**

```python
# tests/conftest.py
import os
import pytest
from pathlib import Path

@pytest.fixture
def tmp_data_dir(tmp_path):
    """Create a temporary data directory mimicking ~/.claude-agent-os/"""
    dirs = ["memory/user", "memory/project", "memory/feedback",
            "memory/reference", "memory/conversation",
            "tasks/archive", "tasks/templates",
            "cron", "logs"]
    for d in dirs:
        (tmp_path / d).mkdir(parents=True)
    return tmp_path

@pytest.fixture
def sample_config(tmp_data_dir):
    """Write a minimal config.yaml and return its path."""
    config_path = tmp_data_dir / "config.yaml"
    config_path.write_text("""
agent:
  name: "Test Agent"
  model: "claude-sonnet-4-6"
  max_concurrent_agents: 2
  auto_pickup_tasks: false

web:
  host: "127.0.0.1"
  port: 8420
  password_hash: ""

telegram:
  bot_token: "test-token"
  allowed_users: ["12345"]

notifications:
  default_channel: "telegram"
""")
    return config_path
```

- [ ] **Step 2: Write failing test for config loading**

```python
# tests/test_config.py
from claude_agent_os.config import AgentConfig, load_config

def test_load_config_from_yaml(sample_config, tmp_data_dir):
    cfg = load_config(tmp_data_dir)
    assert cfg.agent.name == "Test Agent"
    assert cfg.agent.model == "claude-sonnet-4-6"
    assert cfg.web.port == 8420
    assert cfg.telegram.allowed_users == ["12345"]

def test_load_config_defaults_when_missing(tmp_data_dir):
    cfg = load_config(tmp_data_dir)
    assert cfg.agent.name == "Claude Agent OS"
    assert cfg.web.host == "127.0.0.1"

def test_data_dir_paths(tmp_data_dir, sample_config):
    cfg = load_config(tmp_data_dir)
    assert cfg.paths.soul == tmp_data_dir / "soul.md"
    assert cfg.paths.memory == tmp_data_dir / "memory"
    assert cfg.paths.tasks == tmp_data_dir / "tasks"
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
uv run pytest tests/test_config.py -v
```

- [ ] **Step 4: Implement config.py**

```python
# src/claude_agent_os/config.py
"""Configuration management — loads config.yaml with sensible defaults."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml

DEFAULT_DATA_DIR = Path.home() / ".claude-agent-os"

@dataclass
class AgentCfg:
    name: str = "Claude Agent OS"
    model: str = "claude-sonnet-4-6"
    max_concurrent_agents: int = 3
    auto_pickup_tasks: bool = False

@dataclass
class WebCfg:
    host: str = "127.0.0.1"
    port: int = 8420
    password_hash: str = ""

@dataclass
class TelegramCfg:
    bot_token: str = ""
    allowed_users: List[str] = field(default_factory=list)

@dataclass
class NotificationsCfg:
    default_channel: str = "telegram"

@dataclass
class PathsCfg:
    soul: Path = field(default_factory=lambda: Path("soul.md"))
    memory: Path = field(default_factory=lambda: Path("memory"))
    tasks: Path = field(default_factory=lambda: Path("tasks"))
    cron: Path = field(default_factory=lambda: Path("cron"))
    logs: Path = field(default_factory=lambda: Path("logs"))

@dataclass
class AgentConfig:
    agent: AgentCfg = field(default_factory=AgentCfg)
    web: WebCfg = field(default_factory=WebCfg)
    telegram: TelegramCfg = field(default_factory=TelegramCfg)
    notifications: NotificationsCfg = field(default_factory=NotificationsCfg)
    paths: PathsCfg = field(default_factory=PathsCfg)
    data_dir: Path = field(default_factory=lambda: DEFAULT_DATA_DIR)

def load_config(data_dir: Path | None = None) -> AgentConfig:
    """Load config.yaml from data_dir, falling back to defaults."""
    data_dir = data_dir or DEFAULT_DATA_DIR
    config_path = data_dir / "config.yaml"
    raw = {}
    if config_path.exists():
        raw = yaml.safe_load(config_path.read_text()) or {}

    cfg = AgentConfig(data_dir=data_dir)

    # Agent
    if "agent" in raw:
        for k, v in raw["agent"].items():
            if hasattr(cfg.agent, k):
                setattr(cfg.agent, k, v)

    # Web
    if "web" in raw:
        for k, v in raw["web"].items():
            if hasattr(cfg.web, k):
                setattr(cfg.web, k, v)

    # Telegram
    if "telegram" in raw:
        for k, v in raw["telegram"].items():
            if hasattr(cfg.telegram, k):
                setattr(cfg.telegram, k, v)
    # Env override for bot token
    env_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if env_token:
        cfg.telegram.bot_token = env_token

    # Notifications
    if "notifications" in raw:
        for k, v in raw["notifications"].items():
            if hasattr(cfg.notifications, k):
                setattr(cfg.notifications, k, v)

    # Resolve paths relative to data_dir
    cfg.paths = PathsCfg(
        soul=data_dir / "soul.md",
        memory=data_dir / "memory",
        tasks=data_dir / "tasks",
        cron=data_dir / "cron",
        logs=data_dir / "logs",
    )

    return cfg

def save_config(cfg: AgentConfig) -> None:
    """Write config back to config.yaml."""
    data = {
        "agent": {
            "name": cfg.agent.name,
            "model": cfg.agent.model,
            "max_concurrent_agents": cfg.agent.max_concurrent_agents,
            "auto_pickup_tasks": cfg.agent.auto_pickup_tasks,
        },
        "web": {
            "host": cfg.web.host,
            "port": cfg.web.port,
            "password_hash": cfg.web.password_hash,
        },
        "telegram": {
            "bot_token": cfg.telegram.bot_token,
            "allowed_users": cfg.telegram.allowed_users,
        },
        "notifications": {
            "default_channel": cfg.notifications.default_channel,
        },
    }
    config_path = cfg.data_dir / "config.yaml"
    config_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/test_config.py -v
```
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: config system with config.yaml loading and defaults"
```

---

### Task 3: Soul system

**Files:**
- Create: `src/claude_agent_os/soul.py`
- Test: `tests/test_soul.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_soul.py
from claude_agent_os.soul import load_soul, save_soul, DEFAULT_SOUL

def test_load_soul_default_when_missing(tmp_data_dir):
    soul_path = tmp_data_dir / "soul.md"
    content = load_soul(soul_path)
    assert "# Soul" in content

def test_load_soul_from_file(tmp_data_dir):
    soul_path = tmp_data_dir / "soul.md"
    soul_path.write_text("# My Agent\nBe helpful.")
    content = load_soul(soul_path)
    assert content == "# My Agent\nBe helpful."

def test_save_soul(tmp_data_dir):
    soul_path = tmp_data_dir / "soul.md"
    save_soul(soul_path, "# Updated Soul\nNew personality.")
    assert soul_path.read_text() == "# Updated Soul\nNew personality."
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_soul.py -v
```

- [ ] **Step 3: Implement soul.py**

```python
# src/claude_agent_os/soul.py
"""Soul system — personality and identity for the agent."""
from pathlib import Path

DEFAULT_SOUL = """# Soul

You are a personal AI agent. You are direct, technical, and action-oriented.

## Rules
- Be concise and get things done
- Notify via Telegram when tasks complete or fail
- Ask before making destructive changes
"""

def load_soul(soul_path: Path) -> str:
    """Load soul.md, returning default if missing."""
    if soul_path.exists():
        return soul_path.read_text()
    return DEFAULT_SOUL

def save_soul(soul_path: Path, content: str) -> None:
    """Write soul.md."""
    soul_path.parent.mkdir(parents=True, exist_ok=True)
    soul_path.write_text(content)
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_soul.py -v
```
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: soul system — personality loading and persistence"
```

---

### Task 4: Memory manager

**Files:**
- Create: `src/claude_agent_os/memory/__init__.py`
- Create: `src/claude_agent_os/memory/manager.py`
- Create: `src/claude_agent_os/memory/selector.py`
- Test: `tests/test_memory.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_memory.py
import json
from claude_agent_os.memory.manager import MemoryManager

def test_create_memory(tmp_data_dir):
    mgr = MemoryManager(tmp_data_dir / "memory")
    mem = mgr.create(name="test-mem", type="user", tags=["test"],
                     content="Travis likes Python.")
    assert mem["name"] == "test-mem"
    assert (tmp_data_dir / "memory" / "user" / "test-mem.md").exists()

def test_list_memories(tmp_data_dir):
    mgr = MemoryManager(tmp_data_dir / "memory")
    mgr.create(name="mem-1", type="user", tags=[], content="A")
    mgr.create(name="mem-2", type="project", tags=[], content="B")
    all_mems = mgr.list()
    assert len(all_mems) == 2

def test_search_memories(tmp_data_dir):
    mgr = MemoryManager(tmp_data_dir / "memory")
    mgr.create(name="employer", type="user", tags=["work"],
               content="Travis works at Next Link Labs")
    mgr.create(name="hobby", type="user", tags=["personal"],
               content="Travis runs ultramarathons")
    results = mgr.search("Next Link")
    assert len(results) == 1
    assert results[0]["name"] == "employer"

def test_delete_memory(tmp_data_dir):
    mgr = MemoryManager(tmp_data_dir / "memory")
    mgr.create(name="temp", type="user", tags=[], content="delete me")
    mgr.delete("user", "temp")
    assert len(mgr.list()) == 0

def test_rebuild_index(tmp_data_dir):
    mgr = MemoryManager(tmp_data_dir / "memory")
    mgr.create(name="a", type="user", tags=["x"], content="hello")
    # Clear index, rebuild
    mgr._index = {}
    mgr.rebuild_index()
    assert "a" in [m["name"] for m in mgr.list()]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_memory.py -v
```

- [ ] **Step 3: Implement memory/manager.py**

```python
# src/claude_agent_os/memory/manager.py
"""File-based memory manager with frontmatter markdown files."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

VALID_TYPES = ("user", "project", "feedback", "reference", "conversation")

class MemoryManager:
    def __init__(self, memory_dir: Path):
        self.memory_dir = memory_dir
        self._index: dict[str, dict] = {}
        self.rebuild_index()

    def rebuild_index(self) -> None:
        """Scan all .md files and rebuild the in-memory index."""
        self._index = {}
        for type_dir in self.memory_dir.iterdir():
            if not type_dir.is_dir() or type_dir.name.startswith("."):
                continue
            for f in type_dir.glob("*.md"):
                meta, _ = self._parse_file(f)
                if meta:
                    key = f"{type_dir.name}/{f.stem}"
                    self._index[key] = {**meta, "path": str(f)}

    def create(self, name: str, type: str, tags: list[str],
               content: str) -> dict:
        if type not in VALID_TYPES:
            raise ValueError(f"Invalid type: {type}. Must be one of {VALID_TYPES}")
        type_dir = self.memory_dir / type
        type_dir.mkdir(parents=True, exist_ok=True)
        file_path = type_dir / f"{name}.md"
        now = datetime.now(timezone.utc).isoformat()
        frontmatter = (
            f"---\nname: {name}\ntype: {type}\n"
            f"tags: {json.dumps(tags)}\n"
            f"created: {now}\nupdated: {now}\n---\n\n"
        )
        file_path.write_text(frontmatter + content)
        meta = {"name": name, "type": type, "tags": tags,
                "created": now, "updated": now, "path": str(file_path)}
        self._index[f"{type}/{name}"] = meta
        self._save_index()
        return meta

    def get(self, type: str, name: str) -> Optional[dict]:
        key = f"{type}/{name}"
        if key not in self._index:
            return None
        meta = self._index[key]
        _, content = self._parse_file(Path(meta["path"]))
        return {**meta, "content": content}

    def update(self, type: str, name: str, content: str,
               tags: list[str] | None = None) -> dict:
        mem = self.get(type, name)
        if not mem:
            raise FileNotFoundError(f"Memory {type}/{name} not found")
        file_path = Path(mem["path"])
        now = datetime.now(timezone.utc).isoformat()
        new_tags = tags if tags is not None else mem.get("tags", [])
        frontmatter = (
            f"---\nname: {name}\ntype: {type}\n"
            f"tags: {json.dumps(new_tags)}\n"
            f"created: {mem['created']}\nupdated: {now}\n---\n\n"
        )
        file_path.write_text(frontmatter + content)
        self._index[f"{type}/{name}"]["updated"] = now
        self._index[f"{type}/{name}"]["tags"] = new_tags
        self._save_index()
        return self._index[f"{type}/{name}"]

    def delete(self, type: str, name: str) -> None:
        key = f"{type}/{name}"
        if key in self._index:
            Path(self._index[key]["path"]).unlink(missing_ok=True)
            del self._index[key]
            self._save_index()

    def list(self, type: str | None = None) -> list[dict]:
        entries = list(self._index.values())
        if type:
            entries = [e for e in entries if e.get("type") == type]
        return sorted(entries, key=lambda e: e.get("updated", ""), reverse=True)

    def search(self, query: str) -> list[dict]:
        query_lower = query.lower()
        results = []
        for key, meta in self._index.items():
            # Check name and tags
            if query_lower in meta["name"].lower():
                results.append(meta)
                continue
            if any(query_lower in t.lower() for t in meta.get("tags", [])):
                results.append(meta)
                continue
            # Check file content
            path = Path(meta["path"])
            if path.exists():
                content = path.read_text().lower()
                if query_lower in content:
                    results.append(meta)
        return results

    def _parse_file(self, path: Path) -> tuple[dict | None, str]:
        """Parse a markdown file with YAML frontmatter."""
        text = path.read_text()
        match = re.match(r"^---\n(.+?)\n---\n*(.*)", text, re.DOTALL)
        if not match:
            return None, text
        import yaml
        meta = yaml.safe_load(match.group(1)) or {}
        content = match.group(2).strip()
        return meta, content

    def _save_index(self) -> None:
        """Persist index.json."""
        index_path = self.memory_dir / "index.json"
        # Strip path from index entries for portability
        entries = []
        for key, meta in self._index.items():
            entries.append({k: v for k, v in meta.items()})
        index_path.write_text(json.dumps(entries, indent=2, default=str))
```

- [ ] **Step 4: Create memory/__init__.py**

```python
# src/claude_agent_os/memory/__init__.py
```

- [ ] **Step 5: Implement memory/selector.py**

```python
# src/claude_agent_os/memory/selector.py
"""Select relevant memories for a given task context."""
from __future__ import annotations

from pathlib import Path
from claude_agent_os.memory.manager import MemoryManager

def select_memories(mgr: MemoryManager, context: str,
                    max_results: int = 10) -> list[dict]:
    """Return memories most relevant to the given context string."""
    if not context.strip():
        return mgr.list()[:max_results]
    results = mgr.search(context)
    return results[:max_results]

def format_memories_for_prompt(memories: list[dict],
                                memory_dir: Path) -> str:
    """Format selected memories as a string for injection into a Claude prompt."""
    if not memories:
        return ""
    lines = ["# Relevant Memories\n"]
    for mem in memories:
        path = Path(mem["path"])
        if path.exists():
            _, content = _read_content(path)
            lines.append(f"## {mem['name']} ({mem['type']})")
            lines.append(content)
            lines.append("")
    return "\n".join(lines)

def _read_content(path: Path) -> tuple[dict, str]:
    import re, yaml
    text = path.read_text()
    match = re.match(r"^---\n(.+?)\n---\n*(.*)", text, re.DOTALL)
    if not match:
        return {}, text
    meta = yaml.safe_load(match.group(1)) or {}
    return meta, match.group(2).strip()
```

- [ ] **Step 6: Run tests**

```bash
uv run pytest tests/test_memory.py -v
```
Expected: all pass

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: file-based memory system with search, index, and context selection"
```

---

## Phase 2: Task Tracker + Agent Spawner

### Task 5: Task manager

**Files:**
- Create: `src/claude_agent_os/tasks/__init__.py`
- Create: `src/claude_agent_os/tasks/manager.py`
- Test: `tests/test_tasks.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_tasks.py
from claude_agent_os.tasks.manager import TaskManager

def test_create_task(tmp_data_dir):
    mgr = TaskManager(tmp_data_dir / "tasks")
    task = mgr.create(title="Fix bug", description="Auth is broken",
                      priority="high", tags=["bug"])
    assert task["title"] == "Fix bug"
    assert task["status"] == "pending"
    assert task["id"].startswith("t-")

def test_list_tasks(tmp_data_dir):
    mgr = TaskManager(tmp_data_dir / "tasks")
    mgr.create(title="A", description="", priority="low")
    mgr.create(title="B", description="", priority="high")
    assert len(mgr.list()) == 2

def test_update_status(tmp_data_dir):
    mgr = TaskManager(tmp_data_dir / "tasks")
    task = mgr.create(title="Do thing", description="")
    mgr.update_status(task["id"], "in_progress")
    updated = mgr.get(task["id"])
    assert updated["status"] == "in_progress"

def test_archive_completed(tmp_data_dir):
    mgr = TaskManager(tmp_data_dir / "tasks")
    task = mgr.create(title="Done", description="")
    mgr.update_status(task["id"], "completed")
    mgr.archive_completed(max_age_days=0)
    assert len(mgr.list()) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement tasks/manager.py**

Task CRUD with JSON persistence, status transitions, archival. Generate IDs as `t-YYYYMMDD-NNN`. Store active tasks in `active.json`, archive to `archive/YYYY-MM-DD.json`.

- [ ] **Step 4: Run tests, verify pass**

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: task tracker with CRUD, status transitions, and archival"
```

---

### Task 6: Agent spawner

**Files:**
- Create: `src/claude_agent_os/agents/__init__.py`
- Create: `src/claude_agent_os/agents/spawner.py`
- Test: `tests/test_spawner.py`

- [ ] **Step 1: Write failing tests**

Test command building, concurrent agent limiting, and timeout handling. Mock subprocess to avoid needing actual `claude` binary.

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement agents/spawner.py**

Key functions:
- `build_claude_command(prompt, workspace, model, skip_permissions)` → list[str]
- `spawn_agent(task_id, prompt, workspace, ...)` → subprocess handle
- `AgentPool` class managing concurrent agents with max limit
- Timeout enforcement via subprocess timeout
- Result capture and logging

- [ ] **Step 4: Run tests, verify pass**

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: agent spawner — Claude Code subprocess management with pool limits"
```

---

## Phase 3: Cron System

### Task 7: Cron scheduler

**Files:**
- Create: `src/claude_agent_os/cron/__init__.py`
- Create: `src/claude_agent_os/cron/scheduler.py`
- Test: `tests/test_cron.py`

- [ ] **Step 1: Write failing tests**

Test job YAML loading, job listing, manual trigger (mocked agent spawner), and enable/disable.

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement cron/scheduler.py**

Key functions:
- `load_jobs(cron_dir)` → list of job dicts from YAML files
- `CronScheduler` class wrapping APScheduler
- `add_job`, `remove_job`, `enable_job`, `disable_job`
- `trigger_job(name)` — manual trigger
- On trigger: calls agent spawner with job's prompt + workspace
- Run history stored as JSON in logs/

- [ ] **Step 4: Run tests, verify pass**

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: cron scheduler with YAML job definitions and APScheduler"
```

---

## Phase 4: FastAPI Server + Auth + API Routes

### Task 8: Server skeleton + auth

**Files:**
- Create: `src/claude_agent_os/server.py`
- Create: `src/claude_agent_os/auth.py`
- Test: `tests/test_auth.py`

- [ ] **Step 1: Write failing tests for auth**

Test password hashing, session creation, middleware blocking unauthenticated requests (except login).

- [ ] **Step 2: Implement auth.py**

bcrypt password hashing, session cookie middleware, login/logout endpoints.

- [ ] **Step 3: Implement server.py**

FastAPI app factory. On startup: load config, init memory manager, task manager, cron scheduler, mount static files, register API routers. Bind to config host:port.

- [ ] **Step 4: Run tests, verify pass**

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: FastAPI server skeleton with password auth"
```

---

### Task 9: API routes (memory, tasks, cron, soul, chat, logs, settings, webhook)

**Files:**
- Create: `src/claude_agent_os/api/routes_memory.py`
- Create: `src/claude_agent_os/api/routes_tasks.py`
- Create: `src/claude_agent_os/api/routes_cron.py`
- Create: `src/claude_agent_os/api/routes_soul.py`
- Create: `src/claude_agent_os/api/routes_chat.py`
- Create: `src/claude_agent_os/api/routes_logs.py`
- Create: `src/claude_agent_os/api/routes_settings.py`
- Create: `src/claude_agent_os/api/routes_webhook.py`
- Test: `tests/test_api.py`

- [ ] **Step 1: Implement each route file as a FastAPI APIRouter**

Each route file follows the same pattern: import the relevant manager, define CRUD endpoints, return JSON.

- [ ] **Step 2: Write integration tests using FastAPI TestClient**

- [ ] **Step 3: Run tests, verify pass**

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: API routes for memory, tasks, cron, soul, chat, logs, settings, webhooks"
```

---

## Phase 5: Web UI

### Task 10: Web UI templates and static assets

**Files:**
- Create: `src/claude_agent_os/web/templates/base.html`
- Create: `src/claude_agent_os/web/templates/login.html`
- Create: `src/claude_agent_os/web/templates/dashboard.html`
- Create: `src/claude_agent_os/web/templates/chat.html`
- Create: `src/claude_agent_os/web/templates/tasks.html`
- Create: `src/claude_agent_os/web/templates/cron.html`
- Create: `src/claude_agent_os/web/templates/memory.html`
- Create: `src/claude_agent_os/web/templates/soul.html`
- Create: `src/claude_agent_os/web/templates/logs.html`
- Create: `src/claude_agent_os/web/templates/settings.html`
- Create: `src/claude_agent_os/web/static/style.css`
- Create: `src/claude_agent_os/web/static/app.js`

- [ ] **Step 1: Create base.html with nav layout**

Sidebar nav with links to all pages. Dark theme. Responsive.

- [ ] **Step 2: Create login.html — password form**

- [ ] **Step 3: Create dashboard.html — status cards, recent activity**

- [ ] **Step 4: Create tasks.html — kanban board**

- [ ] **Step 5: Create cron.html — job list with run history**

- [ ] **Step 6: Create memory.html — browse, search, edit**

- [ ] **Step 7: Create soul.html — textarea editor with save**

- [ ] **Step 8: Create chat.html — prompt input, response stream**

- [ ] **Step 9: Create logs.html — session transcript viewer**

- [ ] **Step 10: Create settings.html — config editor**

- [ ] **Step 11: Create style.css and app.js**

- [ ] **Step 12: Verify all pages render via browser**

- [ ] **Step 13: Commit**

```bash
git add -A
git commit -m "feat: web UI — all pages with dark theme, kanban tasks, memory browser, chat"
```

---

## Phase 6: Telegram Integration

### Task 11: Telegram bot listener

**Files:**
- Create: `src/claude_agent_os/telegram/__init__.py`
- Create: `src/claude_agent_os/telegram/bot.py`

- [ ] **Step 1: Implement bot.py**

python-telegram-bot Application that:
- Listens for messages from allowed user IDs
- On text message: spawns Claude Code session via agent spawner
- On photo/file: saves to inbox, passes path to Claude
- Sends response back to Telegram
- Access control via config.yaml allowed_users

- [ ] **Step 2: Integrate into server.py startup**

Start Telegram bot in background task on FastAPI startup.

- [ ] **Step 3: Test manually with a real bot token**

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: Telegram bot listener with allowlist and agent spawning"
```

---

## Phase 7: LaunchDaemon + CLI + README

### Task 12: LaunchDaemon installer

**Files:**
- Create: `daemon/com.claude-agent-os.plist.template`
- Modify: `src/claude_agent_os/cli.py` — add `install-daemon` command

- [ ] **Step 1: Create plist template**

- [ ] **Step 2: Add `install-daemon` CLI command**

Generates plist from template (substituting user, paths), copies to `/Library/LaunchDaemons/`, runs `sudo launchctl load`.

- [ ] **Step 3: Add `uninstall-daemon` CLI command**

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: macOS LaunchDaemon installer for always-on operation"
```

---

### Task 13: Update CLI with new commands

**Files:**
- Modify: `src/claude_agent_os/cli.py`

- [ ] **Step 1: Add `server` command** — starts the FastAPI sidecar directly

- [ ] **Step 2: Add `cron` subcommand group** — list, run, enable, disable

- [ ] **Step 3: Add `task` subcommand group** — list, create, status

- [ ] **Step 4: Add `memory` subcommand group** — list, search, create, delete

- [ ] **Step 5: Preserve existing `setup`, `launch`, `doctor`, `info` commands**

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: CLI commands for server, cron, task, and memory management"
```

---

### Task 14: README and final polish

**Files:**
- Rewrite: `README.md`
- Update: `.env.example`
- Update: `.gitignore`

- [ ] **Step 1: Rewrite README for claude-agent-os scope**

- [ ] **Step 2: Update .env.example with new variables**

- [ ] **Step 3: Update .gitignore for new data dirs**

- [ ] **Step 4: Push to GitHub**

```bash
git add -A
git commit -m "docs: rewrite README for claude-agent-os"
git push origin main
```

---

## Summary

| Phase | Tasks | What it delivers |
|-------|-------|-----------------|
| 1: Foundation | 1-4 | Package rename, config, soul, memory |
| 2: Tasks + Agents | 5-6 | Task tracker, agent spawner |
| 3: Cron | 7 | Scheduled jobs with APScheduler |
| 4: Server + API | 8-9 | FastAPI server, auth, all REST endpoints |
| 5: Web UI | 10 | Full dashboard with all pages |
| 6: Telegram | 11 | Direct bot listener |
| 7: Daemon + CLI | 12-14 | LaunchDaemon, CLI commands, README |

Total: 14 tasks across 7 phases. Each phase produces working, testable software.
