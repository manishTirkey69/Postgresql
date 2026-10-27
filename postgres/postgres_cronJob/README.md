# PostgreSQL recurring jobs with `pg_cron`

This lesson schedules SQL inside PostgreSQL using the `pg_cron` extension.
The included job writes a heartbeat row every minute so you can see when the
scheduler ran.

```text
pg_cron scheduler -> SQL command -> cron_job_runs table
                              \--> cron.job_run_details execution record
```

`pg_cron` is an extension, not part of PostgreSQL core. It runs scheduled SQL
in the configured database; unlike the PostgreSQL queue, it does not claim
arbitrary application jobs from a jobs table.

## Start the local PostgreSQL server

From the repository root:

```bash
docker compose -f 18-postgres/postgres_cronJob/docker-compose.yml up --build -d
```

The custom image installs the PostgreSQL 17 `pg_cron` package. Compose enables
the extension through `shared_preload_libraries`, sets `cron.database_name`,
then runs `init.sql` and `demo.sql` when the database volume is initialized.
Scheduled commands use PostgreSQL background workers, avoiding a separate
loopback database login. The local database listens on `127.0.0.1:5434`.

Default local credentials:

```text
database: cron_lab
username: cron_lab
password: local-only-change-me
```

Set `POSTGRES_PASSWORD` in your shell before starting to use a different
password. These defaults are for local learning only. Initialization SQL only
runs the first time a fresh data volume is created.

## Inspect the scheduled job and its runs

The schedule is created automatically during first-time initialization. Inspect
the job list, heartbeat rows, and scheduler history with:

```bash
docker compose -f 18-postgres/postgres_cronJob/docker-compose.yml \
  exec -T postgres psql -U cron_lab -d cron_lab -f /docker-entrypoint-initdb.d/03-inspect.sql
```

`inspect.sql` can be run repeatedly. After the next minute boundary, the
heartbeat and execution history queries should show the job's first run.

The heartbeat table demonstrates successful command effects. The
`cron.job_run_details` view shows scheduler execution outcomes, including
failures. It can be configured to retain only a finite period of history.

## Open the dashboard

Start the FastAPI dashboard in another terminal:

```bash
DATABASE_URL='******127.0.0.1:5434/cron_lab' \
uv run uvicorn app:app \
  --app-dir 18-postgres/postgres_cronJob \
  --host 127.0.0.1 --port 8802
```

Open <http://127.0.0.1:8802/>. The UI lists schedules and recent executions,
lets you schedule the lesson's fixed heartbeat SQL at one of three frequencies,
and lets you unschedule jobs. It does not accept SQL text from the browser.
The UI source is in `18-postgres/frontend_postgres_cronJob/`.

Keep this local demo bound to loopback: it has no user authentication, and
anyone able to access its API can schedule or unschedule the demo jobs.

## Schedule a job manually

For example, schedule a SQL cleanup every day at 02:30 UTC:

```sql
SELECT cron.schedule(
    'delete-old-heartbeats',
    '30 2 * * *',
    $$DELETE FROM public.cron_job_runs WHERE ran_at < now() - interval '30 days';$$
);
```

The expression uses the five cron fields: minute, hour, day of month, month,
and day of week. `cron.timezone=UTC` is set in this Compose example. Change the
job command only to SQL you trust; this is not a place to accept arbitrary
commands from users.

List and stop jobs:

```sql
SELECT jobid, jobname, schedule, active FROM cron.job ORDER BY jobid;
SELECT cron.unschedule(jobid) FROM cron.job WHERE jobname = 'delete-old-heartbeats';
```

`cron.unschedule` permanently removes that schedule. To pause it temporarily,
update the matching `cron.job` row's `active` flag only if your installed
extension version documents that as supported; otherwise unschedule and create
it again.

## Requirements and operational details

- `pg_cron` must be installed on the PostgreSQL server and loaded via
  `shared_preload_libraries`; changing that setting requires a server restart.
- When using background workers, ensure PostgreSQL's
  `max_worker_processes` has capacity for the scheduler and concurrent jobs.
- Only one instance of `pg_cron` should run against a given PostgreSQL data
  directory. In high availability setups, configure it to run on the active
  primary as documented by your platform.
- Jobs execute in the database configured by `cron.database_name`. Schedule
  cross-database work using the extension's documented `cron.schedule_in_database`
  API or use a dedicated worker; do not assume a job can query any database.
- Use a least-privilege database role for scheduled commands in production.
- Monitor `cron.job_run_details`, execution duration, failures, and overlapping
  runs. Keep jobs short and make them safe to rerun.
- Managed PostgreSQL providers differ: some offer `pg_cron`, some require
  enabling it, and some do not support it. Verify the provider's extension
  catalog and configuration before using it.

## Stop and reset

Stop the server but preserve the data volume:

```bash
docker compose -f 18-postgres/postgres_cronJob/docker-compose.yml down
```

To start fresh, remove only this lesson's named volume after confirming you no
longer need its data:

```bash
docker compose -f 18-postgres/postgres_cronJob/docker-compose.yml down -v
```

## When to use cron versus a queue

Use `pg_cron` for recurring database-local SQL such as periodic cleanup,
rollups, or maintenance. Use a queue for irregular work items that arrive from
application requests and need independent processing, retries, or worker
scaling. A scheduled job can enqueue work into a queue, but keep scheduling and
per-job delivery semantics distinct.

The included Compose image and startup configuration are a local demonstration.
Validate package availability and extension behavior against the exact
PostgreSQL version and hosting provider you plan to use.
