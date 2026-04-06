from __future__ import annotations
"""Lightweight Claude OAuth proxy runner for Claude Agent OS.

This wraps the local Claude auth credentials in ~/.claude/.credentials.json and exposes
an Anthropic-compatible /v1/messages endpoint locally. Intended as a companion process
for claude-agent-os when direct Claude CLI auth is unreliable but local OAuth refresh works.
"""

import json
import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import httpx

CREDENTIALS_PATH = Path.home() / ".claude" / ".credentials.json"
TOKEN_REFRESH_URL = "https://api.anthropic.com/v1/oauth/token"
OAUTH_BETA = "claude-code-20250219,oauth-2025-04-20,interleaved-thinking-2025-05-14,context-management-2025-06-27,prompt-caching-scope-2026-01-05"


def _oauth_refresh(refresh_tok: str):
    resp = httpx.post(
        TOKEN_REFRESH_URL,
        json={"grant_type": "refresh_token", "refresh_token": refresh_tok},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["access_token"], data.get("refresh_token", refresh_tok), data.get("expires_in", 3600)


def get_access_token() -> str:
    if os.getenv("ANTHROPIC_OAUTH_KEY"):
        return os.environ["ANTHROPIC_OAUTH_KEY"]

    creds = json.loads(CREDENTIALS_PATH.read_text())
    oauth = creds["claudeAiOauth"]
    expires_at = oauth.get("expiresAt", 0)
    if expires_at and time.time() * 1000 > expires_at - 300000:
        refresh_tok = oauth.get("refreshToken", "")
        if refresh_tok:
            new_access, new_refresh, expires_in = _oauth_refresh(refresh_tok)
            oauth["accessToken"] = new_access
            oauth["refreshToken"] = new_refresh
            oauth["expiresAt"] = int((time.time() + expires_in) * 1000)
            creds["claudeAiOauth"] = oauth
            CREDENTIALS_PATH.write_text(json.dumps(creds))
    return oauth["accessToken"]


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, payload: dict):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/" or self.path == "/health":
            return self._send(200, {"message": "Claude Agent OS Proxy", "endpoints": ["POST /v1/messages", "GET /v1/models"]})
        if self.path == "/v1/models":
            return self._send(200, {"object": "list", "data": [
                {"id": "claude-sonnet-4-6", "object": "model", "owned_by": "anthropic"},
                {"id": "claude-opus-4-6", "object": "model", "owned_by": "anthropic"},
            ]})
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/v1/messages":
            return self._send(404, {"error": "not found"})
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        payload = json.loads(body or b"{}")
        token = get_access_token()
        headers = {
            "x-api-key": token,
            "anthropic-version": "2023-06-01",
            "anthropic-beta": OAUTH_BETA,
            "content-type": "application/json",
        }
        resp = httpx.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload, timeout=120)
        self.send_response(resp.status_code)
        self.send_header("Content-Type", resp.headers.get("content-type", "application/json"))
        self.end_headers()
        self.wfile.write(resp.content)


def main():
    host = os.getenv("CLAUDE_AGENT_PROXY_HOST", "127.0.0.1")
    port = int(os.getenv("CLAUDE_AGENT_PROXY_PORT", "8319"))
    server = HTTPServer((host, port), Handler)
    print(f"Claude Agent OS proxy listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
