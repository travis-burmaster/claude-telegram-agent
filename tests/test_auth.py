"""Tests for authentication utilities."""

import time
from unittest.mock import patch

import pytest

from claude_agent_os.auth import (
    hash_password,
    verify_password,
    create_session,
    validate_session,
    destroy_session,
    clear_all_sessions,
)


class TestPasswordHashing:
    def test_hash_returns_string(self):
        h = hash_password("test123")
        assert isinstance(h, str)
        assert len(h) > 20

    def test_hash_is_different_each_time(self):
        h1 = hash_password("test123")
        h2 = hash_password("test123")
        assert h1 != h2  # Different salts

    def test_verify_correct_password(self):
        h = hash_password("my_password")
        assert verify_password("my_password", h) is True

    def test_verify_wrong_password(self):
        h = hash_password("my_password")
        assert verify_password("wrong_password", h) is False

    def test_verify_empty_password(self):
        h = hash_password("test")
        assert verify_password("", h) is False

    def test_verify_invalid_hash(self):
        assert verify_password("test", "not-a-valid-hash") is False


class TestSessions:
    def setup_method(self):
        clear_all_sessions()

    def test_create_session_returns_token(self):
        token = create_session()
        assert isinstance(token, str)
        assert len(token) > 10

    def test_validate_valid_session(self):
        token = create_session()
        assert validate_session(token) is True

    def test_validate_invalid_session(self):
        assert validate_session("bogus-token") is False

    def test_validate_none_session(self):
        assert validate_session(None) is False

    def test_destroy_session(self):
        token = create_session()
        assert validate_session(token) is True
        destroy_session(token)
        assert validate_session(token) is False

    def test_destroy_none_session(self):
        destroy_session(None)  # Should not raise

    def test_expired_session(self):
        token = create_session()
        # Manually expire the session
        from claude_agent_os.auth import _sessions
        _sessions[token] = time.time() - 1
        assert validate_session(token) is False

    def test_clear_all_sessions(self):
        create_session()
        create_session()
        clear_all_sessions()
        # No sessions should be valid now
        from claude_agent_os.auth import _sessions
        assert len(_sessions) == 0
