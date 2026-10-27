# PostgreSQL as a job queue

This is an alternative implementation to the RabbitMQ lesson. PostgreSQL
stores the jobs themselves; there is no separate broker. A producer inserts a
job row, and workers poll and claim ready rows inside short transactions.

```text
Client -> FastAPI producer -> PostgreSQL queue_jobs <- worker
                                      |                 |
                                      | claim with      +--> Inventory API
                                      | SKIP LOCKED     |
                                      +-----------------+--> completed / retrying / dead_lettered
```

PostgreSQL is a useful queue when job volume is moderate and transactional
consistency with application data matters. It is not automatically as
efficient or feature-rich as a dedicated broker at high message throughput.

## Start PostgreSQL

From the repository root:

```bash
docker compose -f 18-postgres/postgres_queue/docker-compose.yml up -d
```

The database is available on `127.0.0.1:5433`.

Defaults for this local-only example:

```text
database: queue_lab
username: queue_lab
password: local-only-change-me
```

Set a different `POSTGRES_PASSWORD` before starting if desired. The named
Docker volume keeps database contents between restarts. Remove that volume only
if you intentionally want to reset the lesson data.

## Start the Inventory service

In another terminal:

```bash
uv run uvicorn inventory_service:app --app-dir 15-observability \
  --host 127.0.0.1 --port 8601
```

The PostgreSQL worker calls the actual `/inventory/{sku}` endpoint.

## Start the producer API

In another terminal:

```bash
DATABASE_URL='postgresql://queue_lab:local-only-change-me@127.0.0.1:5433/queue_lab' \
uv run uvicorn postgres_app:app \
  --app-dir 18-postgres/postgres_queue \
  --host 127.0.0.1 --port 8701
```

On startup, it creates the `queue_jobs` table and indexes from `schema.sql` if
they do not exist. API documentation is at <http://127.0.0.1:8701/docs>.
Open <http://127.0.0.1:8701/> for the queue dashboard. Its HTML is kept in
`18-postgres/frontend_postgres_queue/`; the API serves it from the same origin.

## Start a worker

In another terminal:

```bash
DATABASE_URL='postgresql://queue_lab:local-only-change-me@127.0.0.1:5433/queue_lab' \
INVENTORY_SERVICE_URL=http://127.0.0.1:8601 \
uv run python 18-postgres/postgres_queue/postgres_worker.py
```

Start more worker processes with the same command to demonstrate concurrent
claims. `FOR UPDATE SKIP LOCKED` lets them claim different jobs without
blocking on the same ready rows.

## Submit and inspect a job

```bash
curl -i -X POST http://127.0.0.1:8701/jobs \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: pg-stock-book-001' \
  -d '{"sku":"book-api"}'
```

The producer returns `202 Accepted` with a `job_id`. Poll for completion:

```bash
curl -sS http://127.0.0.1:8701/jobs/JOB_ID
curl -sS http://127.0.0.1:8701/queue/stats
```

The job transitions through `queued`, `processing`, then `completed`; its
`result` comes from Inventory. Unknown SKUs are permanent failures and become
`dead_lettered`. You can inspect any known job using its job ID. A job can be
retried with the same idempotency key and same payload; a different payload
with an already-used key returns `409 Conflict`.

## Retry and failure behavior

Transient network errors, timeouts, `408`, `429`, and `5xx` responses are
retried up to three total attempts. The retry delay uses capped exponential
backoff: 1 second, then 2 seconds, and at most 30 seconds by default. Configure
`POSTGRES_QUEUE_MAX_BACKOFF_SECONDS` and
`POSTGRES_QUEUE_IDLE_POLL_SECONDS` for local experiments.

Each claim gets a lease and claim token. If the worker dies, the lease expires
and another worker may reclaim that job. The token prevents a stale worker
from completing or failing a job after a newer worker has claimed it.
Permanent errors, or transient errors after the maximum number of attempts,
set status to `dead_lettered` and retain the error on the job row.

## How `SKIP LOCKED` works

The worker selects a small batch of eligible rows in a transaction using
`FOR UPDATE SKIP LOCKED`, then atomically updates them to `processing` before
committing. Other workers skip those locked rows and select different jobs.
The external Inventory request happens after the claim transaction commits;
the database lock is not held during network I/O.

This provides concurrent job claims, not exactly-once side effects. A worker
can still call an external service and crash before marking the job complete.
Make side effects idempotent (for example, send `job_id` as the downstream
idempotency key) and keep retry behavior safe.

## Tests

From the project root:

```bash
uv run pytest 18-postgres/postgres_queue/test_postgres_queue.py
```

These tests validate job JSON normalization and worker success/retry/permanent
failure decisions with fakes. They do not require a running PostgreSQL
instance. The claim SQL uses PostgreSQL-specific features; use a local
PostgreSQL server to validate actual database behavior.

## When to choose PostgreSQL versus a broker

Use the PostgreSQL queue when jobs are moderate in volume, you already operate
PostgreSQL, and creating a job must be atomic with application data. If the
application transaction changes an order and inserts a job row together,
neither change can commit without the other.

Use RabbitMQ, Kafka, or a managed queue when you need higher message throughput,
specialized routing/retention, independent broker scaling, or event replay.
Polling PostgreSQL too frequently can add load, while polling too slowly adds
job latency. Monitor queue age and depth, index active states, and archive or
delete completed rows under a retention policy.

## Configuration and safety

- `DATABASE_URL` is required and must point to PostgreSQL.
- `POSTGRES_QUEUE_POOL_SIZE` controls the asyncpg connection-pool maximum
  (default `10`).
- `INVENTORY_SERVICE_URL` defaults to `http://127.0.0.1:8601`.
- `POSTGRES_QUEUE_IDLE_POLL_SECONDS` defaults to `0.5`.
- `POSTGRES_QUEUE_MAX_BACKOFF_SECONDS` defaults to `30`.

The Compose password is for a local learning environment only. Do not expose
the database port or use this configuration in production; use TLS, secret
management, database roles with least privilege, bounded worker concurrency,
and operational monitoring.
