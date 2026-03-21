"""Soul API routes."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from claude_agent_os.soul import save_soul

router = APIRouter(prefix="/api/soul", tags=["soul"])


@router.get("/")
async def get_soul(request: Request):
    """Get soul.md content."""
    content = request.app.state.soul_content
    return JSONResponse({"content": content})


@router.put("/")
async def update_soul(request: Request):
    """Save soul.md content."""
    body = await request.json()
    content = body.get("content", "")
    cfg = request.app.state.config
    save_soul(cfg.paths.soul, content)
    request.app.state.soul_content = content
    return JSONResponse({"status": "saved"})
