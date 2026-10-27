# Indexes and query plans

An index is an additional data structure PostgreSQL can use to find rows
without scanning the whole table. Indexes can speed up reads, but they consume
storage and add work to inserts, updates, and deletes. Use query plans to
measure whether an index helps the query you actually run.

## Connect and seed sample data

Start the shared database as described in the chapter README, then connect:

```bash
docker compose -f 19-postgres-performance/docker-compose.yml \
  exec postgres psql -U postgres_lab -d postgres_lab
```

Run the seed script from the repository root. The SQL file stays on the host,
so stream it into the database container:

```bash
docker compose -f 19-postgres-performance/docker-compose.yml exec -T postgres \
  psql -U postgres_lab -d postgres_lab \
  < 19-postgres-performance/postgres_indexes/seed.sql
```

Connect interactively for ad hoc queries:

```bash
docker compose -f 19-postgres-performance/docker-compose.yml \
  exec postgres psql -U postgres_lab -d postgres_lab
```

It creates 100,000 deterministic sample rows. Re-running the script resets
only the `index_products` table used by this lesson.

## Compare plans before and after an index

In `psql`, first run:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, name, created_at
FROM index_products
WHERE category = 'category-042'
ORDER BY created_at DESC
LIMIT 20;
```

The table starts without a category/time index. The plan will typically scan
the table and sort rows, though exact choices depend on PostgreSQL version,
table statistics, cached pages, and local system size.

Now add the index and refresh planner statistics:

```sql
CREATE INDEX index_products_category_created_idx
    ON index_products (category, created_at DESC);
ANALYZE index_products;
```

Use `CREATE INDEX IF NOT EXISTS` in the saved `advanced.sql` when repeating
the exercise; the inline statement above is the unindexed-to-indexed change.

The commands are also saved as [`basic.sql`](basic.sql) and
[`advanced.sql`](advanced.sql), so you can compare the plans without copying
SQL from this page.

Run either script from the repository root after loading the seed data:

```bash
docker compose -f 19-postgres-performance/docker-compose.yml exec -T postgres \
  psql -U postgres_lab -d postgres_lab \
  < 19-postgres-performance/postgres_indexes/basic.sql
```

Run the same command with `advanced.sql` to create the composite index and
inspect the updated plan.

Run the same `EXPLAIN (ANALYZE, BUFFERS)` query again. Look for an index scan
or bitmap/index plan, actual execution time, rows visited, and buffer reads.
The planner may still choose a sequential scan when it estimates that is
cheaper; an index does not force a query plan.

Inspect this index and its usage counters:

```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'index_products';

SELECT indexrelname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE relname = 'index_products';
```

Index statistics are cumulative since the last statistics reset and might
include activity from other sessions. They are not a per-query measurement.

## Composite index order

The index starts with `category` because the query filters by category, then
stores `created_at` in descending order to help satisfy the ordering and limit.
An index on `(created_at, category)` would be a different access path and
usually would not help this filter/order combination as directly.

Always check representative filters, ordering, limits, and data sizes. Avoid
adding indexes blindly: every extra index has a write and storage cost.
