-- Run seed.sql first so the query has representative data.
-- Remove the lesson index to compare the baseline plan.
DROP INDEX IF EXISTS index_products_category_created_idx;
ANALYZE index_products;

EXPLAIN (ANALYZE, BUFFERS)
SELECT id, name, created_at
FROM index_products
WHERE category = 'category-042'
ORDER BY created_at DESC
LIMIT 20;
