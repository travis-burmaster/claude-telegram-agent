from __future__ import annotations
"""File-based task manager with JSON persistence."""

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VALID_STATUSES = ("pending", "in_progress", "completed", "failed", "blocked")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


class TaskManager:
    """Manages tasks stored as JSON in a tasks directory."""

    def __init__(self, tasks_dir: Path | str):
        self.tasks_dir = Path(tasks_dir)
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.active_path = self.tasks_dir / "active.json"
        self.archive_dir = self.tasks_dir / "archive"
        self.tasks: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        """Read active.json from disk."""
        if self.active_path.exists():
            with open(self.active_path) as f:
                self.tasks = json.load(f)
        else:
            self.tasks = []

    def _save(self) -> None:
        """Persist tasks to active.json."""
        with open(self.active_path, "w") as f:
            json.dump(self.tasks, f, indent=2)

    def _next_id(self) -> str:
        """Generate a task ID like t-YYYYMMDD-NNN."""
        today = _today_str()
        prefix = f"t-{today}-"
        existing = [
            t["id"] for t in self.tasks
            if t.get("id", "").startswith(prefix)
        ]
        n = len(existing) + 1
        return f"{prefix}{n:03d}"

    def create(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
        tags: list[str] | None = None,
        workspace: str | None = None,
        due: str | None = None,
    ) -> dict[str, Any]:
        """Create a new task and return it."""
        now = _now_iso()
        task = {
            "id": self._next_id(),
            "title": title,
            "description": description,
            "priority": priority,
            "status": "pending",
            "tags": tags or [],
            "workspace": workspace,
            "due": due,
            "created": now,
            "updated": now,
        }
        self.tasks.append(task)
        self._save()
        return task

    def get(self, task_id: str) -> dict[str, Any]:
        """Return a task by ID."""
        for t in self.tasks:
            if t["id"] == task_id:
                return t
        raise KeyError(f"Task '{task_id}' not found")

    def list(self, status: str | None = None) -> list[dict[str, Any]]:
        """List all tasks, optionally filtered by status."""
        if status is not None:
            if status not in VALID_STATUSES:
                raise ValueError(f"Invalid status '{status}'. Must be one of: {VALID_STATUSES}")
            return [t for t in self.tasks if t.get("status") == status]
        return list(self.tasks)

    def update_status(self, task_id: str, status: str) -> dict[str, Any]:
        """Update a task's status."""
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Must be one of: {VALID_STATUSES}")
        task = self.get(task_id)
        task["status"] = status
        task["updated"] = _now_iso()
        self._save()
        return task

    def update(self, task_id: str, **fields: Any) -> dict[str, Any]:
        """Update arbitrary fields on a task."""
        task = self.get(task_id)
        for k, v in fields.items():
            if k == "id":
                continue  # Don't allow changing the ID
            task[k] = v
        task["updated"] = _now_iso()
        self._save()
        return task

    def archive_completed(self, max_age_days: int = 7) -> list[str]:
        """Move completed tasks older than max_age_days to archive/."""
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc)
        archived_ids: list[str] = []
        remaining: list[dict[str, Any]] = []

        for task in self.tasks:
            if task.get("status") == "completed":
                updated = datetime.fromisoformat(task["updated"])
                if hasattr(updated, "tzinfo") and updated.tzinfo is None:
                    updated = updated.replace(tzinfo=timezone.utc)
                age = (now - updated).days
                if age >= max_age_days:
                    archived_ids.append(task["id"])
                    continue
            remaining.append(task)

        if archived_ids:
            # Load existing archive or create new
            archive_path = self.archive_dir / "archived.json"
            existing_archive: list[dict[str, Any]] = []
            if archive_path.exists():
                with open(archive_path) as f:
                    existing_archive = json.load(f)

            archived_tasks = [t for t in self.tasks if t["id"] in archived_ids]
            existing_archive.extend(archived_tasks)

            with open(archive_path, "w") as f:
                json.dump(existing_archive, f, indent=2)

            self.tasks = remaining
            self._save()

        return archived_ids
