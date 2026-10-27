from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx

from postgres_queue import normalize_job
from postgres_worker import InventoryCheckWorker


class FakeQueue:
    def __init__(self, fail_status: str = "retrying") -> None:
        self.completed_result: dict[str, Any] | None = None
        self.failure: dict[str, Any] | None = None
        self.fail_status = fail_status

    async def complete(
        self,
        *,
        job_id: uuid.UUID,
        claim_token: uuid.UUID,
        result: dict[str, Any],
    ) -> bool:
        assert job_id
        assert claim_token
        self.completed_result = result
        return True

    async def fail(
        self,
        *,
        job_id: uuid.UUID,
        claim_token: uuid.UUID,
        error: str,
        retry_delay_seconds: float,
        permanent: bool = False,
    ) -> str:
        self.failure = {
            "job_id": job_id,
            "claim_token": claim_token,
            "error": error,
            "retry_delay_seconds": retry_delay_seconds,
            "permanent": permanent,
        }
        if permanent:
            return "dead_lettered"
        return self.fail_status


def make_job() -> dict[str, Any]:
    return {
        "job_id": uuid.uuid4(),
        "claim_token": uuid.uuid4(),
        "payload": {"sku": "book-api"},
        "attempts": 1,
    }


def test_normalize_job_decodes_jsonb_and_formats_timestamps() -> None:
    created_at = datetime(2026, 10, 14, tzinfo=UTC)
    job = normalize_job(
        {
            "payload": '{"sku":"book-api"}',
            "result": '{"available":42}',
            "created_at": created_at,
            "updated_at": created_at,
        }
    )

    assert job["payload"] == {"sku": "book-api"}
    assert job["result"] == {"available": 42}
    assert job["created_at"] == created_at.isoformat()


def test_worker_completes_successful_inventory_result() -> None:
    queue = FakeQueue()
    job = make_job()
    client = httpx.AsyncClient(
        base_url="http://inventory.test",
        transport=httpx.MockTransport(
            lambda request: (
                httpx.Response(200, json={"sku": "book-api", "available": 42})
                if request.url.path == "/inventory/book-api"
                else httpx.Response(404)
            )
        ),
    )
    worker = InventoryCheckWorker(queue, client)

    outcome = asyncio.run(worker.process(job))
    asyncio.run(client.aclose())

    assert outcome == "completed"
    assert queue.completed_result == {"sku": "book-api", "available": 42}
    assert queue.failure is None


def test_worker_retries_transient_inventory_failure_with_backoff() -> None:
    queue = FakeQueue()
    job = make_job()
    client = httpx.AsyncClient(
        base_url="http://inventory.test",
        transport=httpx.MockTransport(
            lambda request: (
                httpx.Response(503)
                if request.url.path == "/inventory/book-api"
                else httpx.Response(404)
            )
        ),
    )
    worker = InventoryCheckWorker(queue, client)

    outcome = asyncio.run(worker.process(job))
    asyncio.run(client.aclose())

    assert outcome == "retrying"
    assert queue.failure is not None
    assert queue.failure["retry_delay_seconds"] == 1
    assert queue.failure["permanent"] is False


def test_worker_dead_letters_missing_inventory_item() -> None:
    queue = FakeQueue()
    job = make_job()
    client = httpx.AsyncClient(
        base_url="http://inventory.test",
        transport=httpx.MockTransport(
            lambda request: (
                httpx.Response(404)
                if request.url.path == "/inventory/book-api"
                else httpx.Response(500)
            )
        ),
    )
    worker = InventoryCheckWorker(queue, client)

    outcome = asyncio.run(worker.process(job))
    asyncio.run(client.aclose())

    assert outcome == "dead_lettered"
    assert queue.failure is not None
    assert queue.failure["permanent"] is True
