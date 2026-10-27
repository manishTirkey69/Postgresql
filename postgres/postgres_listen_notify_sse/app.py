from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import asyncpg
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
CHANNEL = "job_events"
HEARTBEAT_SECONDS = 15
EVENT_BATCH_SIZE = 100
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://sse_lab:local-only-change-me@127.0.0.1:5435/sse_lab",
)
SCHEMA_PATH = Path(__file__).with_name("schema.sql")
INDEX_PATH = (
    Path(__file__).resolve().parent.parent
    / "frontend_postgres_listen_notify_sse"
    / "index.html"
)


class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class EventBroadcaster:
    def __init__(self) -> None:
        self._clients: set[asyncio.Event] = set()

    def subscribe(self) -> asyncio.Event:
        wake_event = asyncio.Event()
        self._clients.add(wake_event)
        return wake_event

    def unsubscribe(self, wake_event: asyncio.Event) -> None:
        self._clients.discard(wake_event)

    def publish(self) -> None:
        for wake_event in tuple(self._clients):
            wake_event.set()


def parse_last_event_id(value: str | None) -> int:
    if value is None or value == "":
        return 0
    try:
        event_id = int(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid Last-Event-ID") from exc
    if event_id < 0:
        raise HTTPException(status_code=400, detail="Invalid Last-Event-ID")
    return event_id


def format_sse_event(event_id: int, event_type: str, payload: Any) -> str:
    if isinstance(payload, str):
        payload = json.loads(payload)
    data = json.dumps(payload, separators=(",", ":"))
    return f"id: {event_id}\nevent: {event_type}\ndata: {data}\n\n"


async def initialize_schema(pool: asyncpg.Pool) -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    async with pool.acquire() as connection:
        await connection.execute(schema)


def create_app(database_url: str = DATABASE_URL) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
        pool = await asyncpg.create_pool(database_url, min_size=1, max_size=10)
        listener: asyncpg.Connection | None = None
        callback = None
        try:
            await initialize_schema(pool)
            listener = await asyncpg.connect(database_url)
            broadcaster = EventBroadcaster()

            def on_notification(
                _connection: asyncpg.Connection,
                _pid: int,
                channel: str,
                payload: str,
            ) -> None:
                del _connection, _pid
                if channel != CHANNEL:
                    logger.warning("Ignoring unexpected PostgreSQL channel %s", channel)
                    return
                try:
                    int(payload)
                except ValueError:
                    logger.warning("Ignoring invalid outbox event ID on PostgreSQL channel %s", channel)
                    return
                broadcaster.publish()

            callback = on_notification
            await listener.add_listener(CHANNEL, callback)
            application.state.pool = pool
            application.state.listener = listener
            application.state.broadcaster = broadcaster
            yield
        finally:
            if listener is not None:
                if callback is not None:
                    await listener.remove_listener(CHANNEL, callback)
                await listener.close()
            await pool.close()

    app = FastAPI(
        title="PostgreSQL LISTEN/NOTIFY with SSE",
        description="Forward lightweight PostgreSQL notifications to browser EventSource clients.",
        lifespan=lifespan,
    )

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(INDEX_PATH)

    @app.get("/health")
    async def health(request: Request) -> dict[str, str]:
        try:
            async with request.app.state.pool.acquire() as connection:
                await connection.fetchval("SELECT 1")
        except (asyncpg.PostgresError, OSError) as exc:
            raise HTTPException(status_code=503, detail="PostgreSQL is unavailable") from exc
        return {"service": "postgres-listen-notify-sse", "status": "ok"}

    @app.post("/jobs", status_code=201)
    async def create_job(job: JobCreate, request: Request) -> dict[str, Any]:
        async with request.app.state.pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                INSERT INTO jobs (title)
                VALUES ($1)
                RETURNING id, title, created_at
                """,
                job.title,
            )
        if row is None:
            raise RuntimeError("PostgreSQL did not return the inserted job")
        return {
            "id": row["id"],
            "title": row["title"],
            "created_at": row["created_at"].isoformat(),
        }

    @app.get("/events")
    async def events(request: Request) -> StreamingResponse:
        cursor = parse_last_event_id(request.headers.get("last-event-id"))
        broadcaster: EventBroadcaster = request.app.state.broadcaster
        wake_event = broadcaster.subscribe()

        async def stream() -> AsyncGenerator[str, None]:
            nonlocal cursor
            try:
                yield ": connected\n\n"
                while not await request.is_disconnected():
                    wake_event.clear()
                    async with request.app.state.pool.acquire() as connection:
                        rows = await connection.fetch(
                            """
                            SELECT event_id, event_type, payload
                            FROM public.event_outbox
                            WHERE event_id > $1
                            ORDER BY event_id
                            LIMIT $2
                            """,
                            cursor,
                            EVENT_BATCH_SIZE,
                        )
                        if rows:
                            for row in rows:
                                event_id = row["event_id"]
                                event_type = row["event_type"]
                                yield format_sse_event(event_id, event_type, row["payload"])
                                cursor = event_id
                        continue
                    try:
                        await asyncio.wait_for(wake_event.wait(), timeout=HEARTBEAT_SECONDS)
                    except asyncio.TimeoutError:
                        yield ": keepalive\n\n"
            finally:
                broadcaster.unsubscribe(wake_event)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    return app


app = create_app()
