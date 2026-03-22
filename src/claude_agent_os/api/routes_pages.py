from __future__ import annotations
"""HTML page routes — serves Jinja2 templates."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter(tags=["pages"])


def _render(request: Request, template: str, context: dict | None = None):
    """Helper to render a template with common context."""
    templates = request.app.state.templates
    ctx = {"request": request}
    if context:
        ctx.update(context)
    return templates.TemplateResponse(template, ctx)


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return _render(request, "dashboard.html", {"page": "dashboard"})


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    error = request.query_params.get("error")
    return _render(request, "login.html", {"page": "login", "error": error})


@router.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    return _render(request, "chat.html", {"page": "chat"})


@router.get("/tasks", response_class=HTMLResponse)
async def tasks_page(request: Request):
    return _render(request, "tasks.html", {"page": "tasks"})


@router.get("/cron", response_class=HTMLResponse)
async def cron_page(request: Request):
    return _render(request, "cron.html", {"page": "cron"})


@router.get("/memory", response_class=HTMLResponse)
async def memory_page(request: Request):
    return _render(request, "memory.html", {"page": "memory"})


@router.get("/soul", response_class=HTMLResponse)
async def soul_page(request: Request):
    return _render(request, "soul.html", {"page": "soul"})


@router.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request):
    return _render(request, "logs.html", {"page": "logs"})


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return _render(request, "settings.html", {"page": "settings"})
