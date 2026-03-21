"""FastAPI server for claude-agent-os."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from claude_agent_os.config import load_config, AgentConfig
from claude_agent_os.soul import load_soul
from claude_agent_os.memory import MemoryManager
from claude_agent_os.tasks import TaskManager
from claude_agent_os.cron import CronScheduler
from claude_agent_os.agents import AgentPool
from claude_agent_os.auth import AuthMiddleware


def create_app(data_dir: str | Path | None = None) -> FastAPI:
    """Create FastAPI app with all components initialized."""
    cfg = load_config(data_dir)

    # Init managers
    agent_pool = AgentPool(max_concurrent=cfg.agent.max_concurrent_agents)
    memory_mgr = MemoryManager(cfg.paths.memory)
    task_mgr = TaskManager(cfg.paths.tasks)
    cron_scheduler = CronScheduler(cfg.paths.cron, agent_pool, cfg)
    soul_content = load_soul(cfg.paths.soul)

    app = FastAPI(title="Claude Agent OS", version="0.2.0")

    # Store managers in app.state for route access
    app.state.config = cfg
    app.state.agent_pool = agent_pool
    app.state.memory_mgr = memory_mgr
    app.state.task_mgr = task_mgr
    app.state.cron_scheduler = cron_scheduler
    app.state.soul_content = soul_content

    # Auth middleware
    app.add_middleware(AuthMiddleware)

    # Static files and templates
    web_dir = Path(__file__).parent / "web"
    static_dir = web_dir / "static"
    template_dir = web_dir / "templates"

    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    if template_dir.exists():
        app.state.templates = Jinja2Templates(directory=str(template_dir))

    # Register API routers
    from claude_agent_os.api.routes_auth import router as auth_router
    from claude_agent_os.api.routes_memory import router as memory_router
    from claude_agent_os.api.routes_tasks import router as tasks_router
    from claude_agent_os.api.routes_cron import router as cron_router
    from claude_agent_os.api.routes_soul import router as soul_router
    from claude_agent_os.api.routes_chat import router as chat_router
    from claude_agent_os.api.routes_logs import router as logs_router
    from claude_agent_os.api.routes_settings import router as settings_router
    from claude_agent_os.api.routes_webhook import router as webhook_router
    from claude_agent_os.api.routes_pages import router as pages_router

    app.include_router(auth_router)
    app.include_router(memory_router)
    app.include_router(tasks_router)
    app.include_router(cron_router)
    app.include_router(soul_router)
    app.include_router(chat_router)
    app.include_router(logs_router)
    app.include_router(settings_router)
    app.include_router(webhook_router)
    app.include_router(pages_router)

    # Startup/shutdown events
    @app.on_event("startup")
    async def startup():
        cron_scheduler.start()

    @app.on_event("shutdown")
    async def shutdown():
        cron_scheduler.stop()

    return app


def run_server(data_dir: str | Path | None = None) -> None:
    """Run the server with uvicorn."""
    app = create_app(data_dir)
    cfg = app.state.config
    uvicorn.run(app, host=cfg.web.host, port=cfg.web.port)
