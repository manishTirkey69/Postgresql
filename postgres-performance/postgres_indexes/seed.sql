DROP TABLE IF EXISTS index_products;

CREATE TABLE index_products (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    category TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

INSERT INTO index_products (category, name, created_at)
SELECT
    'category-' || lpad((number % 100)::text, 3, '0'),
    'Product ' || number,
    now() - (number % 365) * interval '1 day'
FROM generate_series(1, 100000) AS series(number);

ANALYZE index_products;
