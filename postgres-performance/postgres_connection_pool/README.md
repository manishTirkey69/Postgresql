# Async PostgreSQL connection pooling

Opening a new database connection for every API request adds connection setup
cost and can exhaust PostgreSQL under load. An async connection pool keeps a
bounded number of connections open and lends one to each operation that needs
the database.

This demo uses the repository's existing `asyncpg` dependency and PostgreSQL
service from the chapter root.

First run [`basic_connect.py`](basic_connect.py) to open one connection, issue
a query, and close it. The API below is the advanced step: it creates a bounded
pool once and reuses connections across requests.

```bash
uv run python 19-postgres-performance/postgres_connection_pool/basic_connect.py
```

## Start the API

Start PostgreSQL as described in the chapter README, then from the repository
root run:

```bash
DATABASE_URL='postgresql://postgres_lab:local-only-change-me@127.0.0.1:5436/postgres_lab' \
uv run uvicorn app:app \
  --app-dir 19-postgres-performance/postgres_connection_pool \
  --host 127.0.0.1 --port 8900
```

Open <http://127.0.0.1:8900/docs> or call:

```bash
curl http://127.0.0.1:8900/health
curl http://127.0.0.1:8900/pool
```

The app creates one pool during FastAPI startup and closes it on shutdown.
Each request acquires a connection with an async context manager, which
returns it to the pool even if the query raises an exception.

## Pool configuration

Set these environment variables before starting the app:

```text
POSTGRES_POOL_MIN_SIZE=1
POSTGRES_POOL_MAX_SIZE=10
POSTGRES_POOL_COMMAND_TIMEOUT=10
```

Choose pool sizes based on total database connection capacity, not just this
one process. If there are multiple API processes and workers, their maximum
pool sizes add together. Leave capacity for migrations, monitoring, and
administrative access. A pool is a limit and reuse mechanism, not a query
optimization; tune slow SQL separately with `EXPLAIN ANALYZE`.

The `/pool` route reports the configured limits and current idle count for
learning. Avoid exposing pool diagnostics publicly in a production API.
