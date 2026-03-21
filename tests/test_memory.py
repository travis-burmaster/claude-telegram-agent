"""Tests for the memory manager and selector."""

import json
from pathlib import Path

import pytest

from claude_agent_os.memory.manager import MemoryManager, VALID_TYPES
from claude_agent_os.memory.selector import select_memories, format_memories_for_prompt


class TestMemoryManagerCreate:
    def test_create_returns_entry(self, tmp_path):
        mgr = MemoryManager(tmp_path / "memory")
        entry = mgr.create("Test User", "user", tags=["admin"], content="User info")
        assert entry["name"] == "Test User"
        assert entry["type"] == "user"
        assert entry["tags"] == ["admin"]

    def test_create_writes_file(self, tmp_path):
        mgr = MemoryManager(tmp_path / "memory")
        mgr.create("Test User", "user", content="User info")
        fp = tmp_path / "memory" / "user" / "test_user.md"
        assert fp.exists()
        text = fp.read_text()
        assert "name: Test User" in text
        assert "User info" in text

    def test_create_updates_index(self, tmp_path):
        mgr = MemoryManager(tmp_path / "memory")
        mgr.create("Test User", "user")
        assert len(mgr.index) == 1
        assert mgr.index[0]["name"] == "Test User"

    def test_create_duplicate_raises(self, tmp_path):
        mgr = MemoryManager(tmp_path / "memory")
        mgr.create("Test", "user")
        with pytest.raises(FileExistsError):
            mgr.create("Test", "user")

    def test_create_invalid_type_raises(self, tmp_path):
        mgr = MemoryManager(tmp_path / "memory")
        with pytest.raises(ValueError, match="Invalid memory type"):
            mgr.create("Test", "invalid_type")


class TestMemoryManagerGet:
    def test_get_returns_content(self, tmp_path):
        mgr = MemoryManager(tmp_path / "memory")
        mgr.create("Test", "user", content="Hello world")
        result = mgr.get("user", "Test")
        assert result["content"] == "Hello world"
        assert result["name"] == "Test"

    def test_get_not_found_raises(self, tmp_path):
        mgr = MemoryManager(tmp_path / "memory")
        with pytest.raises(FileNotFoundError):
            mgr.get("user", "Nonexistent")


class TestMemoryManagerUpdate:
    def test_update_content(self, tmp_path):
        mgr = MemoryManager(tmp_path / "memory")
        mgr.create("Test", "user", content="Old")
        result = mgr.update("user", "Test", content="New")
        assert result["content"] == "New"

    def test_update_tags(self, tmp_path):
        mgr = MemoryManager(tmp_path / "memory")
        mgr.create("Test", "user", tags=["old"])
        result = mgr.update("user", "Test", tags=["new", "updated"])
        assert result["tags"] == ["new", "updated"]

    def test_update_not_found_raises(self, tmp_path):
        mgr = MemoryManager(tmp_path / "memory")
        with pytest.raises(FileNotFoundError):
            mgr.update("user", "Missing", content="x")


class TestMemoryManagerDelete:
    def test_delete_removes_file(self, tmp_path):
        mgr = MemoryManager(tmp_path / "memory")
        mgr.create("Test", "user")
        mgr.delete("user", "Test")
        fp = tmp_path / "memory" / "user" / "test.md"
        assert not fp.exists()

    def test_delete_removes_from_index(self, tmp_path):
        mgr = MemoryManager(tmp_path / "memory")
        mgr.create("Test", "user")
        mgr.delete("user", "Test")
        assert len(mgr.index) == 0

    def test_delete_nonexistent_no_error(self, tmp_path):
        mgr = MemoryManager(tmp_path / "memory")
        mgr.delete("user", "Nonexistent")  # Should not raise


class TestMemoryManagerList:
    def test_list_all(self, tmp_path):
        mgr = MemoryManager(tmp_path / "memory")
        mgr.create("A", "user")
        mgr.create("B", "project")
        assert len(mgr.list()) == 2

    def test_list_by_type(self, tmp_path):
        mgr = MemoryManager(tmp_path / "memory")
        mgr.create("A", "user")
        mgr.create("B", "project")
        mgr.create("C", "user")
        result = mgr.list("user")
        assert len(result) == 2
        assert all(e["type"] == "user" for e in result)

    def test_list_empty(self, tmp_path):
        mgr = MemoryManager(tmp_path / "memory")
        assert mgr.list() == []


class TestMemoryManagerSearch:
    def test_search_by_name(self, tmp_path):
        mgr = MemoryManager(tmp_path / "memory")
        mgr.create("Travis Info", "user", content="some content")
        mgr.create("Project Alpha", "project", content="other content")
        results = mgr.search("Travis")
        assert len(results) == 1
        assert results[0]["name"] == "Travis Info"

    def test_search_by_tag(self, tmp_path):
        mgr = MemoryManager(tmp_path / "memory")
        mgr.create("A", "user", tags=["python", "dev"])
        mgr.create("B", "project", tags=["rust"])
        results = mgr.search("python")
        assert len(results) == 1

    def test_search_by_content(self, tmp_path):
        mgr = MemoryManager(tmp_path / "memory")
        mgr.create("A", "user", content="loves coffee")
        mgr.create("B", "user", content="prefers tea")
        results = mgr.search("coffee")
        assert len(results) == 1
        assert results[0]["name"] == "A"

    def test_search_no_results(self, tmp_path):
        mgr = MemoryManager(tmp_path / "memory")
        mgr.create("A", "user", content="hello")
        assert mgr.search("nonexistent") == []


class TestMemoryManagerRebuildIndex:
    def test_rebuild_restores_index(self, tmp_path):
        mgr = MemoryManager(tmp_path / "memory")
        mgr.create("Test", "user", tags=["tag1"], content="content")
        # Manually clear index
        mgr.index = []
        mgr._save_index()
        # Rebuild
        mgr.rebuild_index()
        assert len(mgr.index) == 1
        assert mgr.index[0]["name"] == "Test"


class TestMemorySelector:
    def test_select_memories_returns_results(self, tmp_path):
        mgr = MemoryManager(tmp_path / "memory")
        mgr.create("Python Notes", "reference", tags=["python"], content="Python tips")
        mgr.create("Rust Notes", "reference", tags=["rust"], content="Rust tips")
        results = select_memories(mgr, "python programming")
        assert len(results) >= 1
        names = [r["name"] for r in results]
        assert "Python Notes" in names

    def test_select_respects_max_results(self, tmp_path):
        mgr = MemoryManager(tmp_path / "memory")
        for i in range(20):
            mgr.create(f"Note {i}", "reference", tags=["common"], content="shared keyword")
        results = select_memories(mgr, "common", max_results=5)
        assert len(results) <= 5

    def test_format_memories_empty(self, tmp_path):
        result = format_memories_for_prompt([], tmp_path)
        assert result == ""

    def test_format_memories_includes_content(self, tmp_path):
        mgr = MemoryManager(tmp_path / "memory")
        entry = mgr.create("Test", "user", tags=["tag1"], content="Important info")
        result = format_memories_for_prompt([entry], tmp_path / "memory")
        assert "Test" in result
        assert "Important info" in result
        assert "tag1" in result
