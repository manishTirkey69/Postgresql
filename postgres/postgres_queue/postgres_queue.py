from __future__ import annotations

import json
import os
import uuid
from collections.abc import Mapping
from typing import Any

import asyncpg

DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_LEASE_SECONDS = 60
MAX_PAYLOAD_BYTES = 64 * 1024

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


class IdempotencyConflict(ValueError):
    pass


def postgres_dsn() -> str:
    dsn = os.getenv("DATABASE_URL", "postgresql://queue_lab:local-only-change-me@localhost:5433/queue_lab")
    if not dsn:
        raise RuntimeError("DATABASE_URL must be set for the PostgreSQL queue")
    return dsn


async def create_pool(dsn: str | None = None) -> asyncpg.Pool:
    return await asyncpg.create_pool(
        dsn or postgres_dsn(),
        min_size=1,
        max_size=int(os.getenv("POSTGRES_QUEUE_POOL_SIZE", "10")),
        command_timeout=10,
    )


async def initialize_schema(pool: asyncpg.Pool) -> None:
    with open(SCHEMA_PATH, encoding="utf-8") as schema_file:
        schema_sql = schema_file.read()
    async with pool.acquire() as connection:
        await connection.execute(schema_sql)


def normalize_job(row: Mapping[str, Any]) -> dict[str, Any]:
    job = dict(row)
    for key in ("payload", "result"):
        value = job.get(key)
        if isinstance(value, str):
            job[key] = json.loads(value)
    for key in ("created_at", "updated_at", "available_at", "locked_until"):
        value = job.get(key)
        if value is not None:
            job[key] = value.isoformat()
    return job


class PostgresQueue:
    """A transactional queue backed by PostgreSQL using SKIP LOCKED claims."""

    def __init__(
        self,
        pool: asyncpg.Pool,
        *,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
    ) -> None:
        if lease_seconds < 1:
            raise ValueError("lease_seconds must be positive")
        self.pool = pool
        self.lease_seconds = lease_seconds

    async def enqueue(
        self,
        *,
        idempotency_key: str,
        job_type: str,
        payload: dict[str, Any],
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    ) -> tuple[dict[str, Any], bool]:
        if not idempotency_key or len(idempotency_key) > 128:
            raise ValueError("idempotency_key must contain 1-128 characters")
        if not job_type or len(job_type) > 100:
            raise ValueError("job_type must contain 1-100 characters")
        if max_attempts < 1 or max_attempts > 20:
            raise ValueError("max_attempts must be between 1 and 20")
        payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        if len(payload_json.encode("utf-8")) > MAX_PAYLOAD_BYTES:
            raise ValueError("Queue payload exceeds the 64 KiB limit")

        job_id = uuid.uuid4()
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                row = await connection.fetchrow(
                    """
                    INSERT INTO queue_jobs (
                        job_id, idempotency_key, job_type, payload, status, max_attempts
                    )
                    VALUES ($1, $2, $3, $4::jsonb, 'queued', $5)
                    ON CONFLICT (idempotency_key) DO NOTHING
                    RETURNING *
                    """,
                    job_id,
                    idempotency_key,
                    job_type,
                    payload_json,
                    max_attempts,
                )
                created = row is not None
                if row is None:
                    row = await connection.fetchrow(
                        "SELECT * FROM queue_jobs WHERE idempotency_key = $1 FOR SHARE",
                        idempotency_key,
                    )
                if row is None:
                    raise RuntimeError("Queue job was not stored")
                existing_payload = row["payload"]
                if isinstance(existing_payload, str):
                    existing_payload = json.loads(existing_payload)
                if row["job_type"] != job_type or existing_payload != payload:
                    raise IdempotencyConflict(
                        "Idempotency key was already used for a different job"
                    )
        return normalize_job(row), created

    async def get(self, job_id: uuid.UUID) -> dict[str, Any] | None:
        async with self.pool.acquire() as connection:
            row = await connection.fetchrow(
                "SELECT * FROM queue_jobs WHERE job_id = $1",
                job_id,
            )
        return normalize_job(row) if row is not None else None

    async def claim(self, *, batch_size: int = 1) -> list[dict[str, Any]]:
        if batch_size < 1 or batch_size > 100:
            raise ValueError("batch_size must be between 1 and 100")
        async with self.pool.acquire() as connection:
            await connection.execute(
                """
                UPDATE queue_jobs
                SET status = 'dead_lettered',
                    last_error = COALESCE(last_error, 'Worker lease expired after final attempt'),
                    claim_token = NULL,
                    locked_until = NULL,
                    updated_at = now()
                WHERE status = 'processing'
                  AND locked_until < now()
                  AND attempts >= max_attempts
                """
            )
            rows = await connection.fetch(
                """
                WITH ready AS (
                    SELECT job_id
                    FROM queue_jobs
                    WHERE (
                        status IN ('queued', 'retrying')
                        AND available_at <= now()
                    ) OR (
                        status = 'processing'
                        AND locked_until < now()
                        AND attempts < max_attempts
                    )
                    ORDER BY available_at, created_at
                    FOR UPDATE SKIP LOCKED
                    LIMIT $1
                )
                UPDATE queue_jobs AS job
                SET status = 'processing',
                    attempts = job.attempts + 1,
                    claim_token = gen_random_uuid(),
                    locked_until = now() + ($2 * interval '1 second'),
                    updated_at = now()
                FROM ready
                WHERE job.job_id = ready.job_id
                RETURNING job.*
                """,
                batch_size,
                self.lease_seconds,
            )
        return [normalize_job(row) for row in rows]

    async def complete(
        self,
        *,
        job_id: uuid.UUID,
        claim_token: uuid.UUID,
        result: dict[str, Any],
    ) -> bool:
        async with self.pool.acquire() as connection:
            status = await connection.execute(
                """
                UPDATE queue_jobs
                SET status = 'completed',
                    result = $3::jsonb,
                    last_error = NULL,
                    claim_token = NULL,
                    locked_until = NULL,
                    updated_at = now()
                WHERE job_id = $1
                  AND status = 'processing'
                  AND claim_token = $2
                  AND locked_until > now()
                """,
                job_id,
                claim_token,
                json.dumps(result, separators=(",", ":")),
            )
        return status == "UPDATE 1"

    async def fail(
        self,
        *,
        job_id: uuid.UUID,
        claim_token: uuid.UUID,
        error: str,
        retry_delay_seconds: float,
        permanent: bool = False,
    ) -> str | None:
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                row = await connection.fetchrow(
                    """
                    SELECT attempts, max_attempts
                    FROM queue_jobs
                    WHERE job_id = $1
                      AND status = 'processing'
                      AND claim_token = $2
                      AND locked_until > now()
                    FOR UPDATE
                    """,
                    job_id,
                    claim_token,
                )
                if row is None:
                    return None
                dead = permanent or row["attempts"] >= row["max_attempts"]
                status = "dead_lettered" if dead else "retrying"
                await connection.execute(
                    """
                    UPDATE queue_jobs
                    SET status = $3,
                        available_at = CASE
                            WHEN $3 = 'retrying'
                            THEN now() + ($4 * interval '1 second')
                            ELSE available_at
                        END,
                        last_error = $5,
                        claim_token = NULL,
                        locked_until = NULL,
                        updated_at = now()
                    WHERE job_id = $1 AND claim_token = $2
                    """,
                    job_id,
                    claim_token,
                    status,
                    max(retry_delay_seconds, 0),
                    error[:2000],
                )
        return status

    async def counts(self) -> dict[str, int]:
        async with self.pool.acquire() as connection:
            rows = await connection.fetch(
                "SELECT status, count(*) AS count FROM queue_jobs GROUP BY status"
            )
        return {row["status"]: row["count"] for row in rows}
