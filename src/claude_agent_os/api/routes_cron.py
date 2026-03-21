"""Cron job API routes."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/cron", tags=["cron"])


@router.get("/")
async def list_jobs(request: Request):
    """List all cron jobs."""
    scheduler = request.app.state.cron_scheduler
    jobs = scheduler.list_jobs()
    return JSONResponse({"jobs": jobs})


@router.get("/{name}")
async def get_job(request: Request, name: str):
    """Get a single job's details."""
    scheduler = request.app.state.cron_scheduler
    jobs = scheduler._jobs
    if name not in jobs:
        return JSONResponse({"error": f"Job '{name}' not found"}, status_code=404)
    return JSONResponse({"job": jobs[name]})


@router.post("/")
async def create_job(request: Request):
    """Create a new cron job."""
    scheduler = request.app.state.cron_scheduler
    body = await request.json()
    try:
        job = scheduler.add_job(
            name=body["name"],
            schedule=body["schedule"],
            prompt=body["prompt"],
            workspace=body.get("workspace"),
            model=body.get("model"),
            notify=body.get("notify"),
            timeout=body.get("timeout", 600),
            enabled=body.get("enabled", True),
        )
        return JSONResponse({"job": job}, status_code=201)
    except (ValueError, KeyError) as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.put("/{name}")
async def update_job(request: Request, name: str):
    """Update a cron job (remove + re-add)."""
    scheduler = request.app.state.cron_scheduler
    if name not in scheduler._jobs:
        return JSONResponse({"error": f"Job '{name}' not found"}, status_code=404)
    body = await request.json()
    scheduler.remove_job(name)
    try:
        job = scheduler.add_job(
            name=name,
            schedule=body.get("schedule", "0 * * * *"),
            prompt=body.get("prompt", ""),
            workspace=body.get("workspace"),
            model=body.get("model"),
            notify=body.get("notify"),
            timeout=body.get("timeout", 600),
            enabled=body.get("enabled", True),
        )
        return JSONResponse({"job": job})
    except (ValueError, KeyError) as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.delete("/{name}")
async def delete_job(request: Request, name: str):
    """Delete a cron job."""
    scheduler = request.app.state.cron_scheduler
    scheduler.remove_job(name)
    return JSONResponse({"status": "deleted"})


@router.post("/{name}/trigger")
async def trigger_job(request: Request, name: str):
    """Run a cron job immediately."""
    scheduler = request.app.state.cron_scheduler
    try:
        result = await scheduler.trigger_job(name)
        return JSONResponse({"result": result})
    except KeyError as e:
        return JSONResponse({"error": str(e)}, status_code=404)


@router.post("/{name}/enable")
async def enable_job(request: Request, name: str):
    """Enable a cron job."""
    scheduler = request.app.state.cron_scheduler
    try:
        job = scheduler.enable_job(name)
        return JSONResponse({"job": job})
    except KeyError as e:
        return JSONResponse({"error": str(e)}, status_code=404)


@router.post("/{name}/disable")
async def disable_job(request: Request, name: str):
    """Disable a cron job."""
    scheduler = request.app.state.cron_scheduler
    try:
        job = scheduler.disable_job(name)
        return JSONResponse({"job": job})
    except KeyError as e:
        return JSONResponse({"error": str(e)}, status_code=404)


@router.get("/{name}/history")
async def get_history(request: Request, name: str, limit: int = 20):
    """Get run history for a cron job."""
    scheduler = request.app.state.cron_scheduler
    history = scheduler.get_run_history(name, limit=limit)
    return JSONResponse({"history": history})
