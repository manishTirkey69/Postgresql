from __future__ import annotations

import re
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator

import asyncpg
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from postgres_queue import (
    IdempotencyConflict,
    PostgresQueue,
    create_pool,
    initialize_schema,
    normalize_job,
)

IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
SKU_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
FRONTEND_PATH = Path(__file__).resolve().parent.parent / "frontend_postgres_queue" / "index.html"


class InventoryCheck(BaseModel):
    sku: str = Field(min_length=1, max_length=64)


def create_app(pool: asyncpg.Pool | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
        owns_pool = pool is None
        application.state.pool = pool or await create_pool()
        await initialize_schema(application.state.pool)
        application.state.queue = PostgresQueue(application.state.pool)
        try:
            yield
        finally:
            if owns_pool:
                await application.state.pool.close()

    app = FastAPI(
        title="PostgreSQL queue producer",
        description="Enqueue jobs directly into PostgreSQL; no message broker required.",
        lifespan=lifespan,
    )
    app.state.pool = pool
    app.state.queue = PostgresQueue(pool) if pool is not None else None

    @app.get("/")
    async def frontend() -> FileResponse:
        return FileResponse(FRONTEND_PATH)

    @app.get("/health")
    async def health(request: Request) -> dict[str, str]:
        try:
            async with request.app.state.pool.acquire() as connection:
                await connection.fetchval("SELECT 1")
        except (asyncpg.PostgresError, OSError) as exc:
            raise HTTPException(status_code=503, detail="PostgreSQL is unavailable") from exc
        return {"service": "postgres-queue", "status": "ok"}

    @app.get("/queue/stats")
    async def queue_stats(request: Request) -> dict[str, dict[str, int]]:
        return {"jobs_by_status": await request.app.state.queue.counts()}

    @app.get("/jobs")
    async def list_jobs(
        request: Request,
        limit: int = Query(default=30, ge=1, le=100),
    ) -> list[dict[str, Any]]:
        async with request.app.state.pool.acquire() as connection:
            rows = await connection.fetch(
                "SELECT * FROM queue_jobs ORDER BY created_at DESC LIMIT $1",
                limit,
            )
        return [normalize_job(row) for row in rows]

    @app.post("/jobs", status_code=202)
    async def enqueue(
        body: InventoryCheck,
        request: Request,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=128),
    ) -> dict[str, Any]:
        if not IDEMPOTENCY_PATTERN.fullmatch(idempotency_key):
            raise HTTPException(status_code=422, detail="Invalid Idempotency-Key")
        if not SKU_PATTERN.fullmatch(body.sku):
            raise HTTPException(status_code=422, detail="Invalid SKU")
        try:
            job, created = await request.app.state.queue.enqueue(
                idempotency_key=idempotency_key,
                job_type="inventory.check",
                payload={"sku": body.sku},
            )
        except IdempotencyConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {**job, "duplicate": not created}

    @app.get("/jobs/{job_id}")
    async def get_job(job_id: uuid.UUID, request: Request) -> dict[str, Any]:
        job = await request.app.state.queue.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return job

    return app


app = create_app()
