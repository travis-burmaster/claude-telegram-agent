"""Settings API routes."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from claude_agent_os.auth import hash_password
from claude_agent_os.config import save_config, _dataclass_to_dict

router = APIRouter(prefix="/api/settings", tags=["settings"])

SENSITIVE_FIELDS = {"password_hash", "bot_token"}


def _redact(data: dict) -> dict:
    """Redact sensitive fields from config dict."""
    result = {}
    for k, v in data.items():
        if isinstance(v, dict):
            result[k] = _redact(v)
        elif k in SENSITIVE_FIELDS:
            result[k] = "***" if v else ""
        else:
            result[k] = v
    return result


@router.get("/")
async def get_settings(request: Request):
    """Get current config (with sensitive fields redacted)."""
    cfg = request.app.state.config
    data = {}
    for section in ("agent", "web", "telegram", "notifications", "paths"):
        data[section] = _dataclass_to_dict(getattr(cfg, section))
    return JSONResponse({"settings": _redact(data)})


@router.put("/")
async def update_settings(request: Request):
    """Update config fields."""
    cfg = request.app.state.config
    body = await request.json()

    # Update agent settings
    if "agent" in body:
        for k, v in body["agent"].items():
            if hasattr(cfg.agent, k):
                setattr(cfg.agent, k, v)

    # Update web settings (except password_hash)
    if "web" in body:
        for k, v in body["web"].items():
            if hasattr(cfg.web, k) and k != "password_hash":
                setattr(cfg.web, k, v)

    # Update telegram settings
    if "telegram" in body:
        for k, v in body["telegram"].items():
            if hasattr(cfg.telegram, k):
                setattr(cfg.telegram, k, v)

    # Update notifications
    if "notifications" in body:
        for k, v in body["notifications"].items():
            if hasattr(cfg.notifications, k):
                setattr(cfg.notifications, k, v)

    save_config(cfg)
    return JSONResponse({"status": "saved"})


@router.post("/password")
async def change_password(request: Request):
    """Change the web UI password."""
    body = await request.json()
    new_password = body.get("password", "")
    if not new_password:
        return JSONResponse({"error": "password is required"}, status_code=400)

    cfg = request.app.state.config
    cfg.web.password_hash = hash_password(new_password)
    save_config(cfg)
    return JSONResponse({"status": "password changed"})
