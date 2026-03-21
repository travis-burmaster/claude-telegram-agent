"""Task API routes."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/")
async def list_tasks(request: Request, status: str | None = None):
    """List tasks, optionally filtered by status."""
    mgr = request.app.state.task_mgr
    try:
        tasks = mgr.list(status=status)
        return JSONResponse({"tasks": tasks})
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.get("/{task_id}")
async def get_task(request: Request, task_id: str):
    """Get a single task by ID."""
    mgr = request.app.state.task_mgr
    try:
        task = mgr.get(task_id)
        return JSONResponse({"task": task})
    except KeyError as e:
        return JSONResponse({"error": str(e)}, status_code=404)


@router.post("/")
async def create_task(request: Request):
    """Create a new task."""
    mgr = request.app.state.task_mgr
    body = await request.json()
    try:
        task = mgr.create(
            title=body["title"],
            description=body.get("description", ""),
            priority=body.get("priority", "medium"),
            tags=body.get("tags", []),
            workspace=body.get("workspace"),
            due=body.get("due"),
        )
        return JSONResponse({"task": task}, status_code=201)
    except (ValueError, KeyError) as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.patch("/{task_id}")
async def update_task(request: Request, task_id: str):
    """Update task fields."""
    mgr = request.app.state.task_mgr
    body = await request.json()
    try:
        task = mgr.update(task_id, **body)
        return JSONResponse({"task": task})
    except KeyError as e:
        return JSONResponse({"error": str(e)}, status_code=404)


@router.patch("/{task_id}/status")
async def update_task_status(request: Request, task_id: str):
    """Update task status."""
    mgr = request.app.state.task_mgr
    body = await request.json()
    try:
        task = mgr.update_status(task_id, body["status"])
        return JSONResponse({"task": task})
    except KeyError as e:
        return JSONResponse({"error": str(e)}, status_code=404)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.post("/archive")
async def archive_tasks(request: Request):
    """Trigger archival of completed tasks."""
    mgr = request.app.state.task_mgr
    archived = mgr.archive_completed()
    return JSONResponse({"archived": archived})
