# Transactions, isolation, and row locks

Transactions group database operations so they commit together or roll back
together. PostgreSQL's default isolation level is `READ COMMITTED`: each
statement sees rows committed before that statement began.

This exercise uses two `psql` sessions to show a row lock and a lost update
prevention pattern with `SELECT ... FOR UPDATE`.

Start with [`basic.sql`](basic.sql) for a transaction that applies a debit and
credit together. Continue with [`advanced.sql`](advanced.sql) and the two
session walkthrough below to see how an explicit row lock coordinates
concurrent updates.

Run the basic transaction from the repository root:

```bash
docker compose -f 19-postgres-performance/docker-compose.yml exec -T postgres \
  psql -U postgres_lab -d postgres_lab \
  < 19-postgres-performance/postgres_transactions/basic.sql
```

To run the advanced script, stream it to PostgreSQL from the repository root.
It holds the row lock for ten seconds, giving you time to issue the competing
update from a second terminal:

```bash
docker compose -f 19-postgres-performance/docker-compose.yml exec -T postgres \
  psql -U postgres_lab -d postgres_lab \
  < 19-postgres-performance/postgres_transactions/advanced.sql
```

## Prepare a shared row

Start the chapter's PostgreSQL service and open two terminals. In either
terminal, connect:

```bash
docker compose -f 19-postgres-performance/docker-compose.yml \
  exec postgres psql -U postgres_lab -d postgres_lab
```

Run this setup once:

```sql
CREATE TABLE IF NOT EXISTS bank_accounts (
    account_id INTEGER PRIMARY KEY,
    balance INTEGER NOT NULL CHECK (balance >= 0)
);

INSERT INTO bank_accounts (account_id, balance)
VALUES (1, 100)
ON CONFLICT (account_id) DO UPDATE SET balance = EXCLUDED.balance;
```

## Watch a lock block a competing update

In **Session A**, begin a transaction and lock the account row:

```sql
BEGIN;
SELECT account_id, balance
FROM bank_accounts
WHERE account_id = 1
FOR UPDATE;
```

Leave Session A's transaction open. In **Session B**, run:

```sql
UPDATE bank_accounts
SET balance = balance - 10
WHERE account_id = 1;
```

Session B waits because Session A holds a row lock. Back in Session A, finish
the transaction:

```sql
UPDATE bank_accounts
SET balance = balance - 20
WHERE account_id = 1;
COMMIT;
```

Session B can now continue. Check the final balance:

```sql
SELECT balance FROM bank_accounts WHERE account_id = 1;
```

The row lock makes the read-then-update operation safe from another
transaction changing that row in between. Keep transactions short: locks are
held until commit or rollback.

If a session is left waiting, cancel its query with `Ctrl+C` in `psql`; use
`ROLLBACK;` in the session that owns the open transaction.

## Observe transaction snapshots

With two sessions, run in Session A:

```sql
BEGIN;
SELECT balance FROM bank_accounts WHERE account_id = 1;
```

In Session B, update and commit:

```sql
UPDATE bank_accounts SET balance = balance + 5 WHERE account_id = 1;
COMMIT;
```

Back in Session A, repeat the `SELECT`. Under the default `READ COMMITTED`
isolation, the new statement can see Session B's committed balance. End Session
A with `COMMIT;`.

Use explicit row locks or atomic conditional updates for invariants that need
coordination. Use stricter isolation only when the transaction's consistency
requirements call for it; applications must be prepared to retry serialization
failures where applicable.
