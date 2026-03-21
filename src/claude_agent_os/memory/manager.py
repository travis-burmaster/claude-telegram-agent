"""File-based memory manager with YAML frontmatter and JSON index."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

VALID_TYPES = ("user", "project", "feedback", "reference", "conversation")

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter and content from a markdown string."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    meta = yaml.safe_load(m.group(1)) or {}
    content = m.group(2)
    return meta, content


def _render_frontmatter(meta: dict[str, Any], content: str) -> str:
    """Render YAML frontmatter + content into a markdown string."""
    fm = yaml.dump(meta, default_flow_style=False, sort_keys=False).strip()
    return f"---\n{fm}\n---\n{content}"


class MemoryManager:
    """Manages file-based memories with YAML frontmatter and a JSON index."""

    def __init__(self, memory_dir: Path | str):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.memory_dir / "index.json"
        self.index: list[dict[str, Any]] = []
        self._load_index()

    def _load_index(self) -> None:
        """Load index from disk or rebuild if missing."""
        if self.index_path.exists():
            with open(self.index_path) as f:
                self.index = json.load(f)
        else:
            self.rebuild_index()

    def _save_index(self) -> None:
        """Persist index to disk."""
        with open(self.index_path, "w") as f:
            json.dump(self.index, f, indent=2)

    def _file_path(self, mem_type: str, name: str) -> Path:
        """Return the file path for a memory."""
        slug = name.lower().replace(" ", "_")
        type_dir = self.memory_dir / mem_type
        type_dir.mkdir(parents=True, exist_ok=True)
        return type_dir / f"{slug}.md"

    def _validate_type(self, mem_type: str) -> None:
        if mem_type not in VALID_TYPES:
            raise ValueError(f"Invalid memory type '{mem_type}'. Must be one of: {VALID_TYPES}")

    def create(
        self,
        name: str,
        mem_type: str,
        tags: list[str] | None = None,
        content: str = "",
    ) -> dict[str, Any]:
        """Create a new memory file with YAML frontmatter."""
        self._validate_type(mem_type)
        tags = tags or []
        now = _now_iso()

        meta = {
            "name": name,
            "type": mem_type,
            "tags": tags,
            "created": now,
            "updated": now,
        }

        fp = self._file_path(mem_type, name)
        if fp.exists():
            raise FileExistsError(f"Memory '{name}' of type '{mem_type}' already exists")

        fp.write_text(_render_frontmatter(meta, content))

        entry = {**meta, "file": str(fp.relative_to(self.memory_dir))}
        self.index.append(entry)
        self._save_index()
        return entry

    def get(self, mem_type: str, name: str) -> dict[str, Any]:
        """Return metadata + content for a memory."""
        self._validate_type(mem_type)
        fp = self._file_path(mem_type, name)
        if not fp.exists():
            raise FileNotFoundError(f"Memory '{name}' of type '{mem_type}' not found")

        meta, content = _parse_frontmatter(fp.read_text())
        return {**meta, "content": content}

    def update(
        self,
        mem_type: str,
        name: str,
        content: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Update an existing memory's content and/or tags."""
        self._validate_type(mem_type)
        fp = self._file_path(mem_type, name)
        if not fp.exists():
            raise FileNotFoundError(f"Memory '{name}' of type '{mem_type}' not found")

        meta, old_content = _parse_frontmatter(fp.read_text())

        if content is not None:
            old_content = content
        if tags is not None:
            meta["tags"] = tags
        meta["updated"] = _now_iso()

        fp.write_text(_render_frontmatter(meta, old_content))

        # Update index entry
        for entry in self.index:
            if entry.get("name") == name and entry.get("type") == mem_type:
                entry["updated"] = meta["updated"]
                if tags is not None:
                    entry["tags"] = tags
                break

        self._save_index()
        return {**meta, "content": old_content}

    def delete(self, mem_type: str, name: str) -> None:
        """Remove a memory file and its index entry."""
        self._validate_type(mem_type)
        fp = self._file_path(mem_type, name)
        if fp.exists():
            fp.unlink()

        self.index = [
            e for e in self.index
            if not (e.get("name") == name and e.get("type") == mem_type)
        ]
        self._save_index()

    def list(self, mem_type: str | None = None) -> list[dict[str, Any]]:
        """List all memories, optionally filtered by type."""
        if mem_type is not None:
            self._validate_type(mem_type)
            return [e for e in self.index if e.get("type") == mem_type]
        return list(self.index)

    def search(self, query: str) -> list[dict[str, Any]]:
        """Full-text + tag search across all memories."""
        query_lower = query.lower()
        results = []

        for entry in self.index:
            # Check tags
            tags = entry.get("tags", [])
            if any(query_lower in t.lower() for t in tags):
                results.append(entry)
                continue

            # Check name
            if query_lower in entry.get("name", "").lower():
                results.append(entry)
                continue

            # Check file content
            fp = self.memory_dir / entry.get("file", "")
            if fp.exists():
                text = fp.read_text().lower()
                if query_lower in text:
                    results.append(entry)

        return results

    def rebuild_index(self) -> None:
        """Scan all memory files and rebuild the index."""
        self.index = []
        for type_name in VALID_TYPES:
            type_dir = self.memory_dir / type_name
            if not type_dir.is_dir():
                continue
            for fp in sorted(type_dir.glob("*.md")):
                meta, _ = _parse_frontmatter(fp.read_text())
                if meta:
                    entry = {
                        "name": meta.get("name", fp.stem),
                        "type": meta.get("type", type_name),
                        "tags": meta.get("tags", []),
                        "created": meta.get("created", ""),
                        "updated": meta.get("updated", ""),
                        "file": str(fp.relative_to(self.memory_dir)),
                    }
                    self.index.append(entry)
        self._save_index()
