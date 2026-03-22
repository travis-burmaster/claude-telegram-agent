from __future__ import annotations
"""Authentication middleware and password utilities for claude-agent-os."""

import secrets
import time
from typing import Any

import bcrypt
from fastapi import Request, Response
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# In-memory session store: {token: expiry_timestamp}
_sessions: dict[str, float] = {}

SESSION_DURATION = 86400 * 7  # 7 days


def create_session() -> str:
    """Create a new session and return the token."""
    token = secrets.token_urlsafe(32)
    _sessions[token] = time.time() + SESSION_DURATION
    return token


def validate_session(token: str | None) -> bool:
    """Check if a session token is valid and not expired."""
    if not token:
        return False
    expiry = _sessions.get(token)
    if expiry is None:
        return False
    if time.time() > expiry:
        _sessions.pop(token, None)
        return False
    return True


def destroy_session(token: str | None) -> None:
    """Remove a session."""
    if token:
        _sessions.pop(token, None)


def clear_all_sessions() -> None:
    """Clear all sessions (useful for testing)."""
    _sessions.clear()


SKIP_PREFIXES = ("/login", "/api/webhook/", "/static/")


class AuthMiddleware(BaseHTTPMiddleware):
    """Session cookie auth. Skip for /login, /api/webhook/*, and static files."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        path = request.url.path

        # Skip auth for certain paths
        for prefix in SKIP_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)

        # Check session cookie
        token = request.cookies.get("session")
        if validate_session(token):
            return await call_next(request)

        # Not authenticated — redirect HTML requests, 401 for API
        if path.startswith("/api/"):
            return Response(content='{"error":"unauthorized"}', status_code=401,
                            media_type="application/json")

        return RedirectResponse(url="/login", status_code=302)
