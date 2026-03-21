"""Webhook API routes — external triggers for cron jobs."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from claude_agent_os.auth import verify_password

router = APIRouter(prefix="/api/webhook", tags=["webhook"])


@router.post("/{job_name}")
async def trigger_webhook(request: Request, job_name: str):
    """Trigger a cron job via webhook. Authenticated via X-Password header."""
    cfg = request.app.state.config
    password_hash = cfg.web.password_hash

    # Authenticate via header
    if password_hash:
        provided = request.headers.get("X-Password", "")
        if not verify_password(provided, password_hash):
            return JSONResponse({"error": "unauthorized"}, status_code=401)

    scheduler = request.app.state.cron_scheduler
    try:
        result = await scheduler.trigger_job(job_name)
        return JSONResponse({"result": result})
    except KeyError as e:
        return JSONResponse({"error": str(e)}, status_code=404)
