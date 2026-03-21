"""FastAPI server for claude-agent-os."""

import asyncio
import logging
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

logger = logging.getLogger(__name__)


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

    # Telegram bot (optional — only if bot_token is configured)
    telegram_bot = None
    if cfg.telegram.bot_token:
        from claude_agent_os.telegram.bot import TelegramBot

        telegram_bot = TelegramBot(
            bot_token=cfg.telegram.bot_token,
            allowed_users=cfg.telegram.allowed_users,
            agent_pool=agent_pool,
            soul_path=cfg.paths.soul,
            memory_manager=memory_mgr,
        )
        app.state.telegram_bot = telegram_bot

    # Task worker loop
    task_worker_handle = None

    async def task_worker_loop():
        """Periodically check for pending tasks and auto-assign to agents."""
        interval = 30  # seconds between checks
        while True:
            try:
                if not cfg.agent.auto_pickup_tasks:
                    await asyncio.sleep(interval)
                    continue

                pending = task_mgr.list(status="pending")
                if not pending:
                    await asyncio.sleep(interval)
                    continue

                # Pick highest priority first
                priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
                pending.sort(key=lambda t: priority_order.get(t.get("priority", "medium"), 2))

                for task in pending:
                    if agent_pool.active_count() >= cfg.agent.max_concurrent_agents:
                        break

                    task_id = task["id"]
                    task_mgr.update_status(task_id, "in_progress")
                    logger.info(f"Auto-picking task {task_id}: {task['title']}")

                    prompt = f"Task: {task['title']}\n\n{task.get('description', '')}"
                    workspace = task.get("workspace") or str(Path.home())

                    try:
                        result = await agent_pool.spawn(
                            task_id=task_id,
                            prompt=prompt,
                            workspace=workspace,
                            model=cfg.agent.model,
                            timeout=600,
                        )
                        new_status = "completed" if result.exit_code == 0 else "failed"
                        task_mgr.update(task_id, status=new_status,
                                        result=result.output[:5000],
                                        agent_session=task_id)
                        logger.info(f"Task {task_id} finished: {new_status}")
                    except Exception as e:
                        task_mgr.update_status(task_id, "failed")
                        task_mgr.update(task_id, result=str(e))
                        logger.error(f"Task {task_id} failed: {e}")

            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.error(f"Task worker error: {e}")

            await asyncio.sleep(interval)

    # Startup/shutdown events
    @app.on_event("startup")
    async def startup():
        nonlocal task_worker_handle
        cron_scheduler.start()
        task_worker_handle = asyncio.create_task(task_worker_loop())
        logger.info("Task worker started (auto_pickup=%s)", cfg.agent.auto_pickup_tasks)
        if telegram_bot:
            try:
                await telegram_bot.start()
                logger.info("Telegram bot started")
            except Exception as e:
                logger.error(f"Failed to start Telegram bot: {e}")

    @app.on_event("shutdown")
    async def shutdown():
        nonlocal task_worker_handle
        if task_worker_handle:
            task_worker_handle.cancel()
        cron_scheduler.stop()
        if telegram_bot:
            try:
                await telegram_bot.stop()
            except Exception as e:
                logger.error(f"Error stopping Telegram bot: {e}")

    return app


def run_server(data_dir: str | Path | None = None) -> None:
    """Run the server with uvicorn."""
    app = create_app(data_dir)
    cfg = app.state.config
    uvicorn.run(app, host=cfg.web.host, port=cfg.web.port)
