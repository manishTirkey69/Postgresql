from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg
from fastapi import FastAPI, HTTPException, Request

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres_lab:local-only-change-me@127.0.0.1:5436/postgres_lab",
)
POOL_MIN_SIZE = int(os.getenv("POSTGRES_POOL_MIN_SIZE", "1"))
POOL_MAX_SIZE = int(os.getenv("POSTGRES_POOL_MAX_SIZE", "10"))
POOL_COMMAND_TIMEOUT = float(os.getenv("POSTGRES_POOL_COMMAND_TIMEOUT", "10"))


def validate_pool_settings() -> None:
    if POOL_MIN_SIZE < 1:
        raise RuntimeError("POSTGRES_POOL_MIN_SIZE must be at least 1")
    if POOL_MAX_SIZE < POOL_MIN_SIZE:
        raise RuntimeError(
            "POSTGRES_POOL_MAX_SIZE must be greater than or equal to "
            "POSTGRES_POOL_MIN_SIZE"
        )
    if POOL_COMMAND_TIMEOUT <= 0:
        raise RuntimeError("POSTGRES_POOL_COMMAND_TIMEOUT must be positive")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    validate_pool_settings()
    pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=POOL_MIN_SIZE,
        max_size=POOL_MAX_SIZE,
        command_timeout=POOL_COMMAND_TIMEOUT,
    )
    app.state.pool = pool
    try:
        yield
    finally:
        await pool.close()


app = FastAPI(
    title="PostgreSQL connection pool demo",
    description="A bounded asyncpg pool shared by FastAPI requests.",
    lifespan=lifespan,
)


@app.get("/health")
async def health(request: Request) -> dict[str, str]:
    try:
        async with request.app.state.pool.acquire() as connection:
            await connection.fetchval("SELECT 1")
    except (asyncpg.PostgresError, OSError) as exc:
        raise HTTPException(status_code=503, detail="PostgreSQL is unavailable") from exc
    return {"service": "postgres-pool-demo", "status": "ok"}


@app.get("/pool")
async def pool_status(request: Request) -> dict[str, int]:
    pool: asyncpg.Pool = request.app.state.pool
    return {
        "min_size": pool.get_min_size(),
        "max_size": pool.get_max_size(),
        "idle_connections": pool.get_idle_size(),
        "total_connections": pool.get_size(),
    }
