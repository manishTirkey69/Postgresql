# PostgreSQL `LISTEN`/`NOTIFY` with Server-Sent Events

Yes: PostgreSQL can notify a backend process, and the backend can forward those
notifications to browsers using SSE. PostgreSQL does not send SSE directly to
the browser.

```text
POST /jobs -> PostgreSQL transaction
                ├─ INSERT jobs
                ├─ trigger INSERTs event_outbox row
                └─ NOTIFY job_events with event ID (on commit)
                                      |
                                      v
FastAPI LISTEN -> wakes streams -> query event_outbox after cursor
                                      |
                                      v
                             SSE id + EventSource
```

This lesson runs a FastAPI app, PostgreSQL, and a browser UI in
`18-postgres/frontend_postgres_listen_notify_sse/`. Creating a job inserts a
row; a database trigger publishes a small notification; FastAPI broadcasts the
event to each connected browser.

## Start PostgreSQL

From the repository root:

```bash
docker compose -f 18-postgres/postgres_listen_notify_sse/docker-compose.yml up -d
```

The database listens only on `127.0.0.1:5435`.

```text
database: sse_lab
username: sse_lab
password: local-only-change-me
```

Set `POSTGRES_PASSWORD` in your shell before starting if you want a different
local password. The SQL initialization script runs only when Docker creates a
fresh data volume.

## Run the FastAPI app

From the repository root:

```bash
DATABASE_URL='postgresql://sse_lab:local-only-change-me@127.0.0.1:5435/sse_lab' \
uv run uvicorn app:app \
  --app-dir 18-postgres/postgres_listen_notify_sse \
  --host 127.0.0.1 --port 8801
```

Open <http://127.0.0.1:8801/> in two browser tabs. Submit a job in either tab;
the new job should appear in both. The frontend is served by FastAPI from its
own `frontend_*` directory, so API and SSE requests use the same origin. The
same event stream can be inspected without a browser:

```bash
curl -N http://127.0.0.1:8801/events
```

Create an event from another terminal:

```bash
curl -i -X POST http://127.0.0.1:8801/jobs \
  -H 'Content-Type: application/json' \
  -d '{"title":"PostgreSQL event demo"}'
```

The SSE endpoint emits a named `job_created` event. The browser connects through
the native `EventSource` API and automatically retries a dropped connection.
SSE is server-to-client; the form submits data using an ordinary HTTP `POST`.

## What happens in the database

`schema.sql` creates the `jobs` table, an `event_outbox` table, and an
`AFTER INSERT` trigger. The trigger inserts the event in the same database
transaction as the job, then calls `pg_notify('job_events', event_id)`.
PostgreSQL delivers the notification only after commit, so both the job and its
outbox event are committed together or neither is.

The app uses two kinds of PostgreSQL connections:

- A connection pool handles normal API queries.
- A dedicated connection executes `LISTEN job_events` and stays open to receive
  notifications.

The notification contains only the outbox event ID. It is a wake-up hint, not
the event data; FastAPI queries the durable outbox table to obtain events.
That keeps the notification payload small and lets the SSE stream recover
events even if a notification is missed.

## Fan-out, event IDs, and reconnect

Each connected SSE client has its own wake-up signal. On connect, the server
reads saved events from the outbox; after each event it sends an SSE `id:` field
and advances that stream's cursor. On automatic `EventSource` reconnect, the
browser sends the last received ID in the `Last-Event-ID` request header, and
the server replays later outbox rows. The stream also checks the outbox every
15 seconds in case a notification was missed.

The trigger takes a transaction-scoped advisory lock before assigning an
outbox ID. That makes this demo's event IDs follow commit order, so resuming
from the last ID cannot skip a lower-ID event that commits later. The tradeoff
is that concurrent job inserts are serialized while creating their outbox
events; this is suitable for the lesson, not a high-throughput outbox design.

## Tests

From the project root:

```bash
uv run pytest 18-postgres/postgres_listen_notify_sse/test_app.py
```

The unit tests cover listener wake-up fan-out, SSE event IDs/formatting, and
`Last-Event-ID` validation. They do not require a running PostgreSQL server;
use the manual browser/curl steps above to exercise the complete integration.

## Delivery limits and production guidance

`LISTEN`/`NOTIFY` is still a lightweight signal, not a durable message queue:

- PostgreSQL does not retain notifications for disconnected listeners.
- The outbox makes committed events recoverable after SSE/browser disconnects,
  but this demo does not automatically restore its PostgreSQL listener after a
  database/network failure. It relies on the 15-second outbox scan while the
  app remains running; production apps should also reconnect the listener.
- Each application process that needs notifications must own a listener
  connection. A database notification is delivered to every session listening
  on that channel.
- Authentication, authorization, origin policy, TLS, connection limits, and
  per-user event filtering are outside this local demo.

The outbox should be retained long enough for client cursors to reconnect.
Production systems need a cleanup policy that does not delete rows still
needed by clients. This example replays from the initial cursor on a brand-new
browser connection; an established browser reconnects using its last event ID.

This pattern suits lightweight live dashboards and status updates. Use a
durable queue or event broker when you need message retention, independent
consumer offsets, replay, or stronger delivery guarantees. Use WebSockets when
the client and server both need continuous bidirectional communication.

## Stop the demo

```bash
docker compose -f 18-postgres/postgres_listen_notify_sse/docker-compose.yml down
```

Add `-v` only when you intentionally want to remove this lesson's database
volume and its data.
