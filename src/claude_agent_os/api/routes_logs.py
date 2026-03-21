"""Log API routes."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("/")
async def list_logs(request: Request):
    """List log files."""
    cfg = request.app.state.config
    logs_dir = Path(cfg.paths.logs)
    if not logs_dir.exists():
        return JSONResponse({"logs": []})

    files = sorted(
        [f.name for f in logs_dir.iterdir() if f.is_file()],
        reverse=True,
    )
    return JSONResponse({"logs": files})


@router.get("/{filename}")
async def read_log(request: Request, filename: str):
    """Read a log file's content."""
    cfg = request.app.state.config
    logs_dir = Path(cfg.paths.logs)
    log_path = logs_dir / filename

    # Prevent path traversal
    if ".." in filename or "/" in filename:
        return JSONResponse({"error": "invalid filename"}, status_code=400)

    if not log_path.exists():
        return JSONResponse({"error": "log not found"}, status_code=404)

    content = log_path.read_text()
    return JSONResponse({"filename": filename, "content": content})
