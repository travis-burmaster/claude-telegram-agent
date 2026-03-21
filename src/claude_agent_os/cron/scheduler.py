"""Cron-based task scheduler using APScheduler with YAML job definitions."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class CronScheduler:
    """Schedule and manage recurring Claude agent jobs from YAML definitions."""

    def __init__(self, cron_dir: Path | str, agent_pool: Any, config: Any = None):
        self.cron_dir = Path(cron_dir)
        self.cron_dir.mkdir(parents=True, exist_ok=True)
        self.agent_pool = agent_pool
        self.config = config
        self.logs_dir = (
            Path(config.paths.logs) if config and hasattr(config, "paths") else self.cron_dir.parent / "logs"
        )
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self._scheduler = AsyncIOScheduler()
        self._jobs: dict[str, dict[str, Any]] = {}

    def load_jobs(self) -> list[dict[str, Any]]:
        """Load all YAML job definitions from cron_dir."""
        jobs: list[dict[str, Any]] = []
        for fp in sorted(self.cron_dir.glob("*.yaml")):
            try:
                with open(fp) as f:
                    job = yaml.safe_load(f)
                if job and isinstance(job, dict):
                    jobs.append(job)
            except Exception as e:
                logger.warning("Failed to load job %s: %s", fp, e)
        return jobs

    def _schedule_job(self, job: dict[str, Any]) -> None:
        """Add a job to the APScheduler from a job dict."""
        name = job["name"]
        if not job.get("enabled", True):
            self._jobs[name] = job
            return

        schedule = job["schedule"]
        parts = schedule.strip().split()
        trigger = CronTrigger(
            minute=parts[0] if len(parts) > 0 else "*",
            hour=parts[1] if len(parts) > 1 else "*",
            day=parts[2] if len(parts) > 2 else "*",
            month=parts[3] if len(parts) > 3 else "*",
            day_of_week=parts[4] if len(parts) > 4 else "*",
        )

        self._scheduler.add_job(
            self._run_job,
            trigger,
            args=[name],
            id=name,
            replace_existing=True,
            name=name,
        )
        self._jobs[name] = job

    async def _run_job(self, name: str) -> dict[str, Any]:
        """Execute a cron job via the agent spawner and log the result."""
        job = self._jobs.get(name)
        if not job:
            logger.error("Job '%s' not found", name)
            return {"error": f"Job '{name}' not found"}

        task_id = f"cron-{name}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        prompt = job.get("prompt", "")
        workspace = job.get("workspace")
        model = job.get("model")
        timeout = job.get("timeout", 600)

        if workspace:
            workspace = str(Path(workspace).expanduser())

        try:
            result = await self.agent_pool.spawn(
                task_id=task_id,
                prompt=prompt,
                workspace=workspace,
                model=model,
                timeout=timeout,
            )
            log_entry = {
                "job": name,
                "task_id": task_id,
                "timestamp": _now_iso(),
                "exit_code": result.exit_code,
                "duration": result.duration,
                "output": result.output[:5000],  # Truncate for safety
            }
        except Exception as e:
            log_entry = {
                "job": name,
                "task_id": task_id,
                "timestamp": _now_iso(),
                "exit_code": -1,
                "duration": 0,
                "output": str(e),
                "error": True,
            }

        self._write_log(name, log_entry)
        return log_entry

    def _write_log(self, name: str, entry: dict[str, Any]) -> None:
        """Append a JSON log entry for a cron job run."""
        log_file = self.logs_dir / f"cron-{name}.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def start(self) -> None:
        """Load jobs and start the scheduler."""
        for job in self.load_jobs():
            self._schedule_job(job)
        if not self._scheduler.running:
            self._scheduler.start()

    def stop(self) -> None:
        """Shutdown the scheduler."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)

    def add_job(
        self,
        name: str,
        schedule: str,
        prompt: str,
        workspace: str | None = None,
        model: str | None = None,
        notify: str | None = None,
        timeout: int = 600,
        enabled: bool = True,
    ) -> dict[str, Any]:
        """Create a YAML job file and schedule it."""
        job = {
            "name": name,
            "schedule": schedule,
            "prompt": prompt,
            "workspace": workspace or "~/",
            "model": model or "claude-sonnet-4-6",
            "enabled": enabled,
            "notify": notify or "telegram",
            "timeout": timeout,
        }

        fp = self.cron_dir / f"{name}.yaml"
        with open(fp, "w") as f:
            yaml.dump(job, f, default_flow_style=False, sort_keys=False)

        self._schedule_job(job)
        return job

    def remove_job(self, name: str) -> None:
        """Delete a YAML job file and unschedule it."""
        fp = self.cron_dir / f"{name}.yaml"
        if fp.exists():
            fp.unlink()

        if self._scheduler.running:
            try:
                self._scheduler.remove_job(name)
            except Exception:
                pass

        self._jobs.pop(name, None)

    def enable_job(self, name: str) -> dict[str, Any]:
        """Enable a job and reschedule it."""
        job = self._jobs.get(name)
        if not job:
            raise KeyError(f"Job '{name}' not found")

        job["enabled"] = True
        fp = self.cron_dir / f"{name}.yaml"
        with open(fp, "w") as f:
            yaml.dump(job, f, default_flow_style=False, sort_keys=False)

        if self._scheduler.running:
            self._schedule_job(job)
        return job

    def disable_job(self, name: str) -> dict[str, Any]:
        """Disable a job and unschedule it."""
        job = self._jobs.get(name)
        if not job:
            raise KeyError(f"Job '{name}' not found")

        job["enabled"] = False
        fp = self.cron_dir / f"{name}.yaml"
        with open(fp, "w") as f:
            yaml.dump(job, f, default_flow_style=False, sort_keys=False)

        if self._scheduler.running:
            try:
                self._scheduler.remove_job(name)
            except Exception:
                pass
        return job

    async def trigger_job(self, name: str) -> dict[str, Any]:
        """Run a job immediately, regardless of schedule."""
        if name not in self._jobs:
            raise KeyError(f"Job '{name}' not found")
        return await self._run_job(name)

    def list_jobs(self) -> list[dict[str, Any]]:
        """Return all job definitions with next run time if scheduled."""
        results = []
        for name, job in self._jobs.items():
            entry = dict(job)
            if self._scheduler.running:
                try:
                    sched_job = self._scheduler.get_job(name)
                    if sched_job and sched_job.next_run_time:
                        entry["next_run"] = sched_job.next_run_time.isoformat()
                    else:
                        entry["next_run"] = None
                except Exception:
                    entry["next_run"] = None
            else:
                entry["next_run"] = None
            results.append(entry)
        return results

    def get_run_history(self, name: str, limit: int = 20) -> list[dict[str, Any]]:
        """Read run history from the JSONL log file."""
        log_file = self.logs_dir / f"cron-{name}.jsonl"
        if not log_file.exists():
            return []

        entries: list[dict[str, Any]] = []
        with open(log_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

        return entries[-limit:]
