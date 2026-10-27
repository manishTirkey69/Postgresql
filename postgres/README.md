# PostgreSQL

This chapter explores using PostgreSQL for two different kinds of background
work:

- [PostgreSQL job queue](postgres_queue/README.md) with its
  [frontend](frontend_postgres_queue/index.html) — application workers claim
  individual jobs with `FOR UPDATE SKIP LOCKED`.
- [PostgreSQL cron jobs](postgres_cronJob/README.md) with its
  [frontend](frontend_postgres_cronJob/index.html) — the `pg_cron` extension
  runs SQL on a recurring schedule.
- [PostgreSQL `LISTEN`/`NOTIFY` with SSE](postgres_listen_notify_sse/README.md) —
  forwards lightweight database notifications to connected browsers through
  its [frontend](frontend_postgres_listen_notify_sse/index.html).

These techniques solve different problems: queues process submitted work as it
arrives, a scheduler starts recurring work at specified times, and
`LISTEN`/`NOTIFY` signals connected application processes when a database event
occurs.

For query plans, indexes, transactions, and connection pooling, continue to
[PostgreSQL performance and reliability](../19-postgres-performance/README.md).
