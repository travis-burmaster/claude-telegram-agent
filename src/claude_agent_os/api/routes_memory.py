from __future__ import annotations
"""Memory API routes."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("/")
async def list_memories(request: Request, type: str | None = None):
    """List memories, optionally filtered by type."""
    mgr = request.app.state.memory_mgr
    try:
        memories = mgr.list(mem_type=type)
        return JSONResponse({"memories": memories})
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.get("/search")
async def search_memories(request: Request, q: str = ""):
    """Search memories by query string."""
    mgr = request.app.state.memory_mgr
    if not q:
        return JSONResponse({"memories": []})
    results = mgr.search(q)
    return JSONResponse({"memories": results})


@router.get("/{mem_type}/{name}")
async def get_memory(request: Request, mem_type: str, name: str):
    """Get a single memory by type and name."""
    mgr = request.app.state.memory_mgr
    try:
        memory = mgr.get(mem_type, name)
        return JSONResponse({"memory": memory})
    except FileNotFoundError as e:
        return JSONResponse({"error": str(e)}, status_code=404)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.post("/")
async def create_memory(request: Request):
    """Create a new memory."""
    mgr = request.app.state.memory_mgr
    body = await request.json()
    try:
        entry = mgr.create(
            name=body["name"],
            mem_type=body["type"],
            tags=body.get("tags", []),
            content=body.get("content", ""),
        )
        return JSONResponse({"memory": entry}, status_code=201)
    except FileExistsError as e:
        return JSONResponse({"error": str(e)}, status_code=409)
    except (ValueError, KeyError) as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.put("/{mem_type}/{name}")
async def update_memory(request: Request, mem_type: str, name: str):
    """Update a memory's content and/or tags."""
    mgr = request.app.state.memory_mgr
    body = await request.json()
    try:
        entry = mgr.update(
            mem_type=mem_type,
            name=name,
            content=body.get("content"),
            tags=body.get("tags"),
        )
        return JSONResponse({"memory": entry})
    except FileNotFoundError as e:
        return JSONResponse({"error": str(e)}, status_code=404)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.delete("/{mem_type}/{name}")
async def delete_memory(request: Request, mem_type: str, name: str):
    """Delete a memory."""
    mgr = request.app.state.memory_mgr
    try:
        mgr.delete(mem_type, name)
        return JSONResponse({"status": "deleted"})
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
