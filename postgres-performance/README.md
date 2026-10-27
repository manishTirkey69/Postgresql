# PostgreSQL performance and reliability

This chapter builds on the [PostgreSQL background-work lessons](../18-postgres/README.md)
and focuses on core database behavior that helps APIs stay fast and correct:

1. [Indexes and query plans](postgres_indexes/README.md) — use
   `EXPLAIN ANALYZE` to see how an index changes a query plan.
2. [Transactions and locks](postgres_transactions/README.md) — observe
   transaction isolation and row-level locking from two database sessions.
3. [Connection pooling](postgres_connection_pool/README.md) — reuse a bounded
   set of database connections from an async FastAPI application.

Schema migrations are covered separately in
[03-rest: Database Migrations](../03-rest/topics/04-migrations/README.md).

Each sublesson now has a small starting example and a deeper follow-up:

- [Indexes](postgres_indexes/README.md): compare [`basic.sql`](postgres_indexes/basic.sql) with [`advanced.sql`](postgres_indexes/advanced.sql) after seeding.
- [Transactions](postgres_transactions/README.md): start with the atomic transfer in [`basic.sql`](postgres_transactions/basic.sql), then observe row locking with [`advanced.sql`](postgres_transactions/advanced.sql).
- [Connection pooling](postgres_connection_pool/README.md): run [`basic_connect.py`](postgres_connection_pool/basic_connect.py) once, then compare it with the pooled FastAPI app in `postgres_connection_pool/app.py`.

## Start the local database

From the repository root:

```bash
docker compose -f 19-postgres-performance/docker-compose.yml up -d
```

This local-only PostgreSQL instance listens on `127.0.0.1:5436`.

```text
database: postgres_lab
username: postgres_lab
password: local-only-change-me
```

Set `POSTGRES_PASSWORD` before starting to choose another local password.
Each lesson documents its own setup and cleanup steps. The database is shared
between lessons; do not run cleanup commands that remove its volume unless you
intend to discard all lesson data.
