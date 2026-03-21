"""Tests for the task manager."""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from claude_agent_os.tasks.manager import TaskManager, VALID_STATUSES


class TestTaskCreate:
    def test_create_returns_task(self, tmp_path):
        mgr = TaskManager(tmp_path / "tasks")
        task = mgr.create("Build feature", description="Do the thing")
        assert task["title"] == "Build feature"
        assert task["status"] == "pending"
        assert task["priority"] == "medium"
        assert task["id"].startswith("t-")

    def test_create_with_all_fields(self, tmp_path):
        mgr = TaskManager(tmp_path / "tasks")
        task = mgr.create(
            "Urgent task",
            description="ASAP",
            priority="high",
            tags=["urgent"],
            workspace="/tmp/ws",
            due="2026-04-01",
        )
        assert task["priority"] == "high"
        assert task["tags"] == ["urgent"]
        assert task["workspace"] == "/tmp/ws"
        assert task["due"] == "2026-04-01"

    def test_create_persists_to_file(self, tmp_path):
        mgr = TaskManager(tmp_path / "tasks")
        mgr.create("Test")
        assert (tmp_path / "tasks" / "active.json").exists()
        data = json.loads((tmp_path / "tasks" / "active.json").read_text())
        assert len(data) == 1

    def test_sequential_ids(self, tmp_path):
        mgr = TaskManager(tmp_path / "tasks")
        t1 = mgr.create("First")
        t2 = mgr.create("Second")
        # Both should have same date prefix but different sequence
        assert t1["id"] != t2["id"]
        assert t1["id"][-3:] == "001"
        assert t2["id"][-3:] == "002"


class TestTaskGet:
    def test_get_returns_task(self, tmp_path):
        mgr = TaskManager(tmp_path / "tasks")
        created = mgr.create("Test")
        result = mgr.get(created["id"])
        assert result["title"] == "Test"

    def test_get_not_found_raises(self, tmp_path):
        mgr = TaskManager(tmp_path / "tasks")
        with pytest.raises(KeyError):
            mgr.get("t-99999999-001")


class TestTaskList:
    def test_list_all(self, tmp_path):
        mgr = TaskManager(tmp_path / "tasks")
        mgr.create("A")
        mgr.create("B")
        assert len(mgr.list()) == 2

    def test_list_by_status(self, tmp_path):
        mgr = TaskManager(tmp_path / "tasks")
        t1 = mgr.create("A")
        mgr.create("B")
        mgr.update_status(t1["id"], "in_progress")
        assert len(mgr.list("in_progress")) == 1
        assert len(mgr.list("pending")) == 1

    def test_list_invalid_status_raises(self, tmp_path):
        mgr = TaskManager(tmp_path / "tasks")
        with pytest.raises(ValueError):
            mgr.list("invalid_status")

    def test_list_empty(self, tmp_path):
        mgr = TaskManager(tmp_path / "tasks")
        assert mgr.list() == []


class TestTaskUpdateStatus:
    def test_update_status(self, tmp_path):
        mgr = TaskManager(tmp_path / "tasks")
        task = mgr.create("Test")
        result = mgr.update_status(task["id"], "completed")
        assert result["status"] == "completed"

    def test_all_valid_statuses(self, tmp_path):
        mgr = TaskManager(tmp_path / "tasks")
        for status in VALID_STATUSES:
            task = mgr.create(f"Task {status}")
            result = mgr.update_status(task["id"], status)
            assert result["status"] == status

    def test_invalid_status_raises(self, tmp_path):
        mgr = TaskManager(tmp_path / "tasks")
        task = mgr.create("Test")
        with pytest.raises(ValueError):
            mgr.update_status(task["id"], "bad_status")


class TestTaskUpdate:
    def test_update_fields(self, tmp_path):
        mgr = TaskManager(tmp_path / "tasks")
        task = mgr.create("Test")
        result = mgr.update(task["id"], title="Updated", priority="high")
        assert result["title"] == "Updated"
        assert result["priority"] == "high"

    def test_update_cannot_change_id(self, tmp_path):
        mgr = TaskManager(tmp_path / "tasks")
        task = mgr.create("Test")
        original_id = task["id"]
        mgr.update(task["id"], id="fake-id")
        assert mgr.get(original_id)["id"] == original_id


class TestTaskArchive:
    def test_archive_old_completed(self, tmp_path):
        mgr = TaskManager(tmp_path / "tasks")
        task = mgr.create("Old done")
        mgr.update_status(task["id"], "completed")
        # Manually backdate the updated timestamp
        for t in mgr.tasks:
            if t["id"] == task["id"]:
                old_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
                t["updated"] = old_time
        mgr._save()

        archived = mgr.archive_completed(max_age_days=7)
        assert task["id"] in archived
        assert len(mgr.tasks) == 0
        assert (tmp_path / "tasks" / "archive" / "archived.json").exists()

    def test_archive_keeps_recent_completed(self, tmp_path):
        mgr = TaskManager(tmp_path / "tasks")
        task = mgr.create("Recent done")
        mgr.update_status(task["id"], "completed")
        archived = mgr.archive_completed(max_age_days=7)
        assert archived == []
        assert len(mgr.tasks) == 1

    def test_archive_ignores_non_completed(self, tmp_path):
        mgr = TaskManager(tmp_path / "tasks")
        task = mgr.create("Still pending")
        archived = mgr.archive_completed(max_age_days=0)
        assert archived == []


class TestTaskPersistence:
    def test_reload_from_disk(self, tmp_path):
        mgr1 = TaskManager(tmp_path / "tasks")
        mgr1.create("Persistent")
        # Create new manager instance pointing at same dir
        mgr2 = TaskManager(tmp_path / "tasks")
        assert len(mgr2.list()) == 1
        assert mgr2.list()[0]["title"] == "Persistent"
