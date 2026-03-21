"""Tests for the cron scheduler."""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import yaml

from claude_agent_os.cron.scheduler import CronScheduler


@pytest.fixture
def cron_dir(tmp_path):
    d = tmp_path / "cron"
    d.mkdir()
    return d


@pytest.fixture
def logs_dir(tmp_path):
    d = tmp_path / "logs"
    d.mkdir()
    return d


@pytest.fixture
def mock_pool():
    pool = MagicMock()
    result = MagicMock()
    result.exit_code = 0
    result.duration = 1.5
    result.output = "Job completed successfully"
    pool.spawn = AsyncMock(return_value=result)
    return pool


@pytest.fixture
def mock_config(tmp_path):
    cfg = MagicMock()
    cfg.paths.logs = tmp_path / "logs"
    return cfg


@pytest.fixture
def scheduler(cron_dir, mock_pool, mock_config):
    return CronScheduler(cron_dir, mock_pool, mock_config)


class TestLoadJobs:
    def test_empty_dir(self, scheduler):
        jobs = scheduler.load_jobs()
        assert jobs == []

    def test_loads_yaml_files(self, scheduler, cron_dir):
        job = {
            "name": "test-job",
            "schedule": "*/5 * * * *",
            "prompt": "Do something",
            "enabled": True,
        }
        with open(cron_dir / "test-job.yaml", "w") as f:
            yaml.dump(job, f)

        jobs = scheduler.load_jobs()
        assert len(jobs) == 1
        assert jobs[0]["name"] == "test-job"

    def test_skips_invalid_yaml(self, scheduler, cron_dir):
        (cron_dir / "bad.yaml").write_text(": : : not valid yaml [[[")
        jobs = scheduler.load_jobs()
        # Should not crash, just skip
        assert isinstance(jobs, list)


class TestAddJob:
    def test_creates_yaml_file(self, scheduler, cron_dir):
        scheduler.add_job("my-job", "0 * * * *", "Check status")
        fp = cron_dir / "my-job.yaml"
        assert fp.exists()
        with open(fp) as f:
            data = yaml.safe_load(f)
        assert data["name"] == "my-job"
        assert data["schedule"] == "0 * * * *"
        assert data["prompt"] == "Check status"

    def test_returns_job_dict(self, scheduler):
        job = scheduler.add_job("my-job", "0 * * * *", "Check status")
        assert job["name"] == "my-job"
        assert job["enabled"] is True

    def test_job_added_to_internal_state(self, scheduler):
        scheduler.add_job("my-job", "0 * * * *", "Check status")
        assert "my-job" in scheduler._jobs

    def test_custom_parameters(self, scheduler):
        job = scheduler.add_job(
            "my-job", "0 * * * *", "Check status",
            workspace="/tmp/ws",
            model="claude-opus-4",
            notify="slack",
            timeout=120,
            enabled=False,
        )
        assert job["workspace"] == "/tmp/ws"
        assert job["model"] == "claude-opus-4"
        assert job["notify"] == "slack"
        assert job["timeout"] == 120
        assert job["enabled"] is False


class TestRemoveJob:
    def test_removes_yaml_file(self, scheduler, cron_dir):
        scheduler.add_job("my-job", "0 * * * *", "Check status")
        assert (cron_dir / "my-job.yaml").exists()
        scheduler.remove_job("my-job")
        assert not (cron_dir / "my-job.yaml").exists()

    def test_removes_from_internal_state(self, scheduler):
        scheduler.add_job("my-job", "0 * * * *", "Check status")
        scheduler.remove_job("my-job")
        assert "my-job" not in scheduler._jobs

    def test_remove_nonexistent_no_error(self, scheduler):
        scheduler.remove_job("nonexistent")  # Should not raise


class TestEnableDisable:
    def test_disable_job(self, scheduler, cron_dir):
        scheduler.add_job("my-job", "0 * * * *", "Check")
        job = scheduler.disable_job("my-job")
        assert job["enabled"] is False
        with open(cron_dir / "my-job.yaml") as f:
            data = yaml.safe_load(f)
        assert data["enabled"] is False

    def test_enable_job(self, scheduler, cron_dir):
        scheduler.add_job("my-job", "0 * * * *", "Check", enabled=False)
        job = scheduler.enable_job("my-job")
        assert job["enabled"] is True

    def test_disable_nonexistent_raises(self, scheduler):
        with pytest.raises(KeyError):
            scheduler.disable_job("nonexistent")

    def test_enable_nonexistent_raises(self, scheduler):
        with pytest.raises(KeyError):
            scheduler.enable_job("nonexistent")


class TestTriggerJob:
    @pytest.mark.asyncio
    async def test_trigger_runs_agent(self, scheduler, mock_pool):
        scheduler.add_job("my-job", "0 * * * *", "Check status")
        result = await scheduler.trigger_job("my-job")
        mock_pool.spawn.assert_called_once()
        assert result["exit_code"] == 0

    @pytest.mark.asyncio
    async def test_trigger_nonexistent_raises(self, scheduler):
        with pytest.raises(KeyError):
            await scheduler.trigger_job("nonexistent")

    @pytest.mark.asyncio
    async def test_trigger_logs_result(self, scheduler, mock_pool):
        scheduler.add_job("my-job", "0 * * * *", "Check status")
        await scheduler.trigger_job("my-job")
        log_file = scheduler.logs_dir / "cron-my-job.jsonl"
        assert log_file.exists()
        with open(log_file) as f:
            entry = json.loads(f.readline())
        assert entry["job"] == "my-job"
        assert entry["exit_code"] == 0


class TestListJobs:
    def test_empty(self, scheduler):
        assert scheduler.list_jobs() == []

    def test_lists_added_jobs(self, scheduler):
        scheduler.add_job("job-a", "0 * * * *", "A")
        scheduler.add_job("job-b", "0 * * * *", "B")
        jobs = scheduler.list_jobs()
        names = [j["name"] for j in jobs]
        assert "job-a" in names
        assert "job-b" in names


class TestRunHistory:
    def test_empty_history(self, scheduler):
        history = scheduler.get_run_history("nonexistent")
        assert history == []

    @pytest.mark.asyncio
    async def test_history_after_run(self, scheduler, mock_pool):
        scheduler.add_job("my-job", "0 * * * *", "Check")
        await scheduler.trigger_job("my-job")
        history = scheduler.get_run_history("my-job")
        assert len(history) == 1
        assert history[0]["job"] == "my-job"

    @pytest.mark.asyncio
    async def test_history_limit(self, scheduler, mock_pool):
        scheduler.add_job("my-job", "0 * * * *", "Check")
        for _ in range(5):
            await scheduler.trigger_job("my-job")
        history = scheduler.get_run_history("my-job", limit=3)
        assert len(history) == 3
