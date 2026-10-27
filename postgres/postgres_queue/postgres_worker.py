from __future__ import annotations

import asyncio
import logging
import os
import uuid
from typing import Any
from urllib.parse import quote

import httpx

from postgres_queue import PostgresQueue, create_pool, initialize_schema

logger = logging.getLogger("postgres_queue_worker")
INVENTORY_URL = os.getenv("INVENTORY_SERVICE_URL", "http://127.0.0.1:8601").rstrip("/")
MAX_BACKOFF_SECONDS = float(os.getenv("POSTGRES_QUEUE_MAX_BACKOFF_SECONDS", "30"))
IDLE_POLL_SECONDS = float(os.getenv("POSTGRES_QUEUE_IDLE_POLL_SECONDS", "0.5"))


class InventoryCheckWorker:
    def __init__(self, queue: PostgresQueue, inventory_client: Any) -> None:
        self.queue = queue
        self.inventory_client = inventory_client

    async def process(self, job: dict[str, Any]) -> str:
        payload = job["payload"]
        claim_token = job["claim_token"]
        try:
            response = await self.inventory_client.get(
                f"/inventory/{quote(payload['sku'], safe='')}",
                headers={"X-Request-ID": str(job["job_id"])},
            )
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            return await self._fail(job, claim_token, str(exc))

        if response.status_code == 404:
            status = await self.queue.fail(
                job_id=job["job_id"],
                claim_token=claim_token,
                error="SKU not found",
                retry_delay_seconds=0,
                permanent=True,
            )
            return status or "lease_lost"
        if response.status_code >= 500 or response.status_code in {408, 429}:
            return await self._fail(job, claim_token, f"Inventory HTTP {response.status_code}")
        if not response.is_success:
            status = await self.queue.fail(
                job_id=job["job_id"],
                claim_token=claim_token,
                error=f"Inventory rejected request with HTTP {response.status_code}",
                retry_delay_seconds=0,
                permanent=True,
            )
            return status or "lease_lost"

        try:
            result = response.json()
        except ValueError as exc:
            return await self._fail(job, claim_token, f"Inventory returned invalid JSON: {exc}")

        completed = await self.queue.complete(
            job_id=job["job_id"],
            claim_token=claim_token,
            result=result,
        )
        return "completed" if completed else "lease_lost"

    async def _fail(
        self,
        job: dict[str, Any],
        claim_token: uuid.UUID,
        reason: str,
    ) -> str:
        attempts = int(job["attempts"])
        delay = min(2 ** max(attempts - 1, 0), MAX_BACKOFF_SECONDS)
        status = await self.queue.fail(
            job_id=job["job_id"],
            claim_token=claim_token,
            error=reason,
            retry_delay_seconds=delay,
        )
        if status is None:
            return "lease_lost"
        logger.warning(
            "inventory_check_failed",
            extra={
                "job_id": str(job["job_id"]),
                "attempt": attempts,
                "status": status,
                "error": reason,
            },
        )
        return status


async def run_worker() -> None:
    pool = await create_pool()
    await initialize_schema(pool)
    queue = PostgresQueue(pool)
    client = httpx.AsyncClient(base_url=INVENTORY_URL, timeout=httpx.Timeout(3.0))
    worker = InventoryCheckWorker(queue, client)
    logger.info("postgres_queue_worker_started")
    try:
        while True:
            jobs = await queue.claim(batch_size=1)
            if not jobs:
                await asyncio.sleep(IDLE_POLL_SECONDS)
                continue
            for job in jobs:
                try:
                    await worker.process(job)
                except Exception:
                    logger.exception("postgres_queue_job_failed", extra={"job_id": str(job["job_id"])})
                    await queue.fail(
                        job_id=job["job_id"],
                        claim_token=job["claim_token"],
                        error="Unexpected worker failure; lease will be retried",
                        retry_delay_seconds=IDLE_POLL_SECONDS,
                    )
    finally:
        await client.aclose()
        await pool.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    asyncio.run(run_worker())
