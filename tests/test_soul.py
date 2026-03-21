"""Tests for the soul system."""

from pathlib import Path

from claude_agent_os.soul import DEFAULT_SOUL, load_soul, save_soul


class TestLoadSoul:
    def test_returns_default_when_no_file(self, tmp_path):
        soul_path = tmp_path / "soul.md"
        result = load_soul(soul_path)
        assert result == DEFAULT_SOUL

    def test_loads_existing_file(self, tmp_path):
        soul_path = tmp_path / "soul.md"
        soul_path.write_text("Custom soul content")
        result = load_soul(soul_path)
        assert result == "Custom soul content"

    def test_loads_empty_file(self, tmp_path):
        soul_path = tmp_path / "soul.md"
        soul_path.write_text("")
        result = load_soul(soul_path)
        assert result == ""


class TestSaveSoul:
    def test_creates_file(self, tmp_path):
        soul_path = tmp_path / "soul.md"
        save_soul(soul_path, "New soul")
        assert soul_path.read_text() == "New soul"

    def test_creates_parent_dirs(self, tmp_path):
        soul_path = tmp_path / "nested" / "dir" / "soul.md"
        save_soul(soul_path, "Nested soul")
        assert soul_path.read_text() == "Nested soul"

    def test_overwrites_existing(self, tmp_path):
        soul_path = tmp_path / "soul.md"
        soul_path.write_text("Old")
        save_soul(soul_path, "New")
        assert soul_path.read_text() == "New"

    def test_round_trip(self, tmp_path):
        soul_path = tmp_path / "soul.md"
        save_soul(soul_path, "Round trip content")
        assert load_soul(soul_path) == "Round trip content"
