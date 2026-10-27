from __future__ import annotations

import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Literal
from urllib.parse import urlsplit

import asyncpg
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://cron_lab:local-only-change-me@127.0.0.1:5434/cron_lab",
)
FRONTEND_PATH = (
    Path(__file__).resolve().parent.parent / "frontend_postgres_cronJob" / "index.html"
)
JOB_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.-]{0,47}$")
SCHEDULES = {
    "every_minute": "* * * * *",
    "every_five_minutes": "*/5 * * * *",
    "hourly": "0 * * * *",
}
ScheduleChoice = Literal["every_minute", "every_five_minutes", "hourly"]


class ScheduleRequest(BaseModel):
    job_name: str = Field(min_length=1, max_length=48)
    frequency: ScheduleChoice


def validate_database_url(database_url: str) -> None:
    parsed = urlsplit(database_url)
    if (
        parsed.scheme not in {"postgres", "postgresql"}
        or not parsed.netloc
        or not parsed.path.strip("/")
    ):
        raise RuntimeError(
            "DATABASE_URL must be a PostgreSQL URL, for example "
            "'postgresql://cron_lab:password@127.0.0.1:5434/cron_lab'"
        )


def create_app(database_url: str = DATABASE_URL) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
        validate_database_url(database_url)
        pool = await asyncpg.create_pool(database_url, min_size=1, max_size=5)
        application.state.pool = pool
        try:
            yield
        finally:
            await pool.close()

    app = FastAPI(
        title="PostgreSQL pg_cron dashboard",
        description="Inspect and schedule the lesson's safe heartbeat SQL jobs.",
        lifespan=lifespan,
    )

    @app.get("/")
    async def frontend() -> FileResponse:
        return FileResponse(FRONTEND_PATH)

    @app.get("/health")
    async def health(request: Request) -> dict[str, str]:
        try:
            async with request.app.state.pool.acquire() as connection:
                await connection.fetchval("SELECT 1")
                await connection.fetchval("SELECT 1 FROM cron.job LIMIT 1")
        except (asyncpg.PostgresError, OSError) as exc:
            raise HTTPException(
                status_code=503,
                detail="PostgreSQL or pg_cron is unavailable",
            ) from exc
        return {"service": "postgres-cron-dashboard", "status": "ok"}

    @app.get("/api/cron/jobs")
    async def list_jobs(request: Request) -> list[dict[str, object]]:
        async with request.app.state.pool.acquire() as connection:
            rows = await connection.fetch(
                """
                SELECT jobid, jobname, schedule, command, active, username
                FROM cron.job
                ORDER BY jobid
                """
            )
        return [dict(row) for row in rows]

    @app.get("/api/cron/runs")
    async def list_runs(request: Request) -> list[dict[str, object]]:
        async with request.app.state.pool.acquire() as connection:
            rows = await connection.fetch(
                """
                SELECT jobid, runid, status, return_message, start_time, end_time
                FROM cron.job_run_details
                ORDER BY start_time DESC
                LIMIT 50
                """
            )
        return [dict(row) for row in rows]

    @app.post("/api/cron/jobs", status_code=201)
    async def schedule_job(
        body: ScheduleRequest,
        request: Request,
    ) -> dict[str, int | str]:
        if not JOB_NAME_PATTERN.fullmatch(body.job_name):
            raise HTTPException(status_code=422, detail="Invalid job name")
        schedule = SCHEDULES[body.frequency]
        async with request.app.state.pool.acquire() as connection:
            job_id = await connection.fetchval(
                """
                SELECT cron.schedule(
                    $1,
                    $2,
                    format('SELECT public.record_cron_job_run(%L)', $1)
                )
                """,
                body.job_name,
                schedule,
            )
        return {
            "jobid": job_id,
            "job_name": body.job_name,
            "schedule": schedule,
        }

    @app.delete("/api/cron/jobs/{job_id}")
    async def unschedule_job(job_id: int, request: Request) -> dict[str, bool]:
        if job_id < 1:
            raise HTTPException(status_code=422, detail="Job ID must be positive")
        async with request.app.state.pool.acquire() as connection:
            removed = await connection.fetchval(
                "SELECT cron.unschedule($1)",
                job_id,
            )
        if not removed:
            raise HTTPException(status_code=404, detail="Cron job not found")
        return {"removed": True}

    return app


app = create_app()
