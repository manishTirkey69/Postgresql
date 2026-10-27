-- Run seed.sql first, then compare this plan with basic.sql.
CREATE INDEX IF NOT EXISTS index_products_category_created_idx
    ON index_products (category, created_at DESC);
ANALYZE index_products;

EXPLAIN (ANALYZE, BUFFERS)
SELECT id, name, created_at
FROM index_products
WHERE category = 'category-042'
ORDER BY created_at DESC
LIMIT 20;

-- Indexes speed some reads but add storage and write costs. Inspect usage:
SELECT indexrelname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE relname = 'index_products';
