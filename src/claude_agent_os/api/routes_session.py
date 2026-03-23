from __future__ import annotations
"""API routes for session management and live log streaming."""

import asyncio
import time

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

router = APIRouter(prefix="/api/session", tags=["session"])


def _get_session_mgr(request: Request):
    return request.app.state.session_mgr


# ── REST endpoints ───────────────────────────────────────────────


@router.get("/status")
async def session_status(request: Request):
    """Return current session state, uptime, and health info."""
    mgr = _get_session_mgr(request)
    return mgr.status()


@router.post("/start")
async def session_start(request: Request):
    """Start the Claude Code session."""
    mgr = _get_session_mgr(request)
    await mgr.start()
    return mgr.status()


@router.post("/stop")
async def session_stop(request: Request):
    """Gracefully stop the session."""
    mgr = _get_session_mgr(request)
    await mgr.stop()
    return mgr.status()


@router.post("/restart")
async def session_restart(request: Request):
    """Stop and restart the session."""
    mgr = _get_session_mgr(request)
    await mgr.restart()
    return mgr.status()


@router.get("/logs")
async def session_logs(request: Request, n: int = 100):
    """Return the most recent n log lines."""
    mgr = _get_session_mgr(request)
    return {"lines": mgr.get_recent_logs(n)}


# ── WebSocket for live log streaming ─────────────────────────────


@router.websocket("/ws/logs")
async def session_logs_ws(websocket: WebSocket):
    """Stream session logs to the client in real-time."""
    await websocket.accept()

    mgr = websocket.app.state.session_mgr
    queue = mgr.subscribe()

    try:
        while True:
            entry = await queue.get()
            await websocket.send_json({
                "timestamp": entry.timestamp,
                "stream": entry.stream,
                "line": entry.line,
            })
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        mgr.unsubscribe(queue)
