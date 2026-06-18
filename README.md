# 🐘 PostgreSQL Advanced Objects Tutorial

![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Advanced-blue)
![PLpgSQL](https://img.shields.io/badge/PLpgSQL-Functions-success)
![Database](https://img.shields.io/badge/Database-Tutorial-orange)

## 📚 Topics Covered

- 👀 Views
- ⚡ Materialized Views
- 🔢 Sequences
- 🛠 Functions
- 📥 Function Parameters (`IN`, `OUT`, `INOUT`)
- 🚀 Procedures
- 🎯 Triggers
- 📋 Custom Types (ENUM)
- 🔒 Domains
- 📊 Aggregates
- ➕ Custom Operators
- 🧮 Custom Aggregate Functions
- 🌍 Collations
- 🔍 Full Text Search (FTS)

---

# 👀 Views

A **View** is a virtual table created from a SQL query.

### Create View

```sql
CREATE OR REPLACE VIEW ranchi_customers AS
SELECT
    customer_name,
    city
FROM customers
WHERE city = 'Ranchi';
```

### Query View

```sql
SELECT * FROM ranchi_customers;
```

### Why Use Views?

✅ Simplify complex queries

✅ Hide sensitive columns

✅ Reusable query logic

---

# ⚡ Materialized Views

Unlike normal views, a Materialized View stores the query result physically.

### Create Materialized View

```sql
CREATE MATERIALIZED VIEW customer_total_sales AS
SELECT
    customer_id,
    SUM(amount) total_sales
FROM orders
GROUP BY customer_id;
```

### Query

```sql
SELECT * FROM customer_total_sales;
```

### Insert New Data

```sql
INSERT INTO orders
(customer_id, product_name, amount)
VALUES
(1, 'Headphone', 2000);
```

### Check Again

```sql
SELECT * FROM customer_total_sales;
```

⚠️ Data will NOT change automatically.

### Refresh

```sql
REFRESH MATERIALIZED VIEW customer_total_sales;
```

### Verify

```sql
SELECT * FROM customer_total_sales;
```

### Use Cases

- Reporting dashboards
- Analytics
- Heavy aggregation queries

---

# 🔢 Sequences

A sequence generates unique numeric values.

---

## Basic Sequence

```sql
CREATE SEQUENCE invoice_seq;
```

```sql
SELECT nextval('invoice_seq');
```

---

## Find Sequence Behind SERIAL

```sql
SELECT pg_get_serial_sequence(
    'customers',
    'customer_id'
);
```

---

## Custom Increment

```sql
CREATE SEQUENCE mysequence
INCREMENT 5
START 100;
```

Output:

```text
100
105
110
115
...
```

---

## Descending Sequence

```sql
CREATE SEQUENCE three
INCREMENT -1
MINVALUE 1
MAXVALUE 3
START 3
CYCLE;
```

Output:

```text
3
2
1
3
2
1
...
```

---

## Sequence Owned By Column

### Table

```sql
CREATE TABLE order_details(
    order_id SERIAL,
    item_id INT NOT NULL,
    item_text VARCHAR NOT NULL,
    price DEC(10,2) NOT NULL,
    PRIMARY KEY(order_id, item_id)
);
```

### Sequence

```sql
CREATE SEQUENCE order_item_id
START 10
INCREMENT 10
MINVALUE 10
OWNED BY order_details.item_id;
```

### Insert Data

```sql
INSERT INTO order_details(
    order_id,
    item_id,
    item_text,
    price
)
VALUES
(100, nextval('order_item_id'),'DVD Player',100),
(100, nextval('order_item_id'),'Android TV',550),
(100, nextval('order_item_id'),'Speaker',250);
```

---

# 🛠 Functions

Functions return a value and can be used inside SQL queries.

---

## Function Without Arguments

```sql
CREATE OR REPLACE FUNCTION greet()
RETURNS TEXT
AS $$
BEGIN
    RETURN 'Hi';
END;
$$ LANGUAGE plpgsql;
```

```sql
SELECT greet();
```

---

## Function With Arguments

```sql
CREATE OR REPLACE FUNCTION greet(name TEXT)
RETURNS TEXT
AS $$
BEGIN
    RETURN 'Hello ' || name;
END;
$$ LANGUAGE plpgsql;
```

```sql
SELECT greet('Manish');
```

---

## Mathematical Function

```sql
CREATE OR REPLACE FUNCTION add_numbers(
    a INTEGER,
    b INTEGER
)
RETURNS INTEGER
AS $$
BEGIN
    RETURN a + b;
END;
$$ LANGUAGE plpgsql;
```

```sql
SELECT add_numbers(12,2);
```

---

## Returning Table

```sql
CREATE OR REPLACE FUNCTION get_customer(
    p_customer_id INTEGER
)
RETURNS TABLE (
    customer_id INTEGER,
    customer_name VARCHAR,
    city VARCHAR
)
AS $$
BEGIN
    RETURN QUERY
    SELECT *
    FROM customers
    WHERE customer_id = p_customer_id;
END;
$$ LANGUAGE plpgsql;
```

```sql
SELECT * FROM get_customer(1);
```

---

## Default Parameters

```sql
CREATE OR REPLACE FUNCTION greet(
    name TEXT DEFAULT 'Guest'
)
RETURNS TEXT
AS $$
BEGIN
    RETURN 'Hello ' || name;
END;
$$ LANGUAGE plpgsql;
```

```sql
SELECT greet();
```

---

# 📥 Function Parameters

## IN Parameter (Default)

```sql
CREATE OR REPLACE FUNCTION square(
    IN num INTEGER
)
RETURNS INTEGER
AS $$
BEGIN
    RETURN num * num;
END;
$$ LANGUAGE plpgsql;
```

```sql
SELECT square(5);
```

---

## OUT Parameter

```sql
CREATE OR REPLACE FUNCTION get_stats(
    OUT total_customers INTEGER
)
AS $$
BEGIN
    SELECT COUNT(*)
    INTO total_customers
    FROM customers;
END;
$$ LANGUAGE plpgsql;
```

```sql
SELECT * FROM get_stats();
```

---

## Multiple OUT Parameters

```sql
CREATE OR REPLACE FUNCTION get_customer_stats(
    OUT total_customers INT,
    OUT total_orders INT
)
AS $$
BEGIN

    SELECT COUNT(*)
    INTO total_customers
    FROM customers;

    SELECT COUNT(*)
    INTO total_orders
    FROM orders;

END;
$$ LANGUAGE plpgsql;
```

```sql
SELECT * FROM get_customer_stats();
```

---

## GST Calculator Example

```sql
CREATE OR REPLACE FUNCTION calculate_gst(
    amount NUMERIC,
    gst_rate NUMERIC
)
RETURNS NUMERIC
AS $$
BEGIN
    RETURN amount * gst_rate / 100;
END;
$$ LANGUAGE plpgsql;
```

```sql
SELECT calculate_gst(1000,18);
```

---

# 🚀 Procedures

Procedures perform actions but do not return values like functions.

---

## Delete Records Procedure

```sql
CREATE OR REPLACE PROCEDURE delete_small_orders(
    min_amount NUMERIC
)
LANGUAGE plpgsql
AS $$
BEGIN
    DELETE
    FROM orders
    WHERE amount < min_amount;
END;
$$;
```

```sql
CALL delete_small_orders(1000);
```

---

## Print Message

```sql
CREATE OR REPLACE PROCEDURE greet_proc(
    name TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE NOTICE 'Hello %', name;
END;
$$;
```

```sql
CALL greet_proc('Manish');
```

---

## Using Variables

```sql
CREATE OR REPLACE PROCEDURE count_orders()
LANGUAGE plpgsql
AS $$
DECLARE
    total INT;
BEGIN

    SELECT COUNT(*)
    INTO total
    FROM orders;

    RAISE NOTICE 'Total Orders = %', total;

END;
$$;
```

```sql
CALL count_orders();
```

### 📌 RAISE NOTICE

Equivalent to:

```python
print()
```

in Python.

---

# 🎯 Triggers

Triggers execute automatically when database events occur.

---

## Trigger Function

```sql
CREATE OR REPLACE FUNCTION log_new_customer()
RETURNS TRIGGER
AS $$
BEGIN
    RAISE NOTICE 'New customer inserted';
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

---

## Create Trigger

```sql
CREATE TRIGGER customer_insert_trigger
BEFORE INSERT
ON customers
FOR EACH ROW
EXECUTE FUNCTION log_new_customer();
```

---

## Test Trigger

```sql
INSERT INTO customers
(customer_name, city)
VALUES
('Bob', 'Pune');
```

---

# 📋 Custom Types (ENUM)

---

## Create ENUM

```sql
CREATE TYPE order_status AS ENUM (
    'pending',
    'processing',
    'completed'
);
```

---

## Use ENUM

```sql
CREATE TABLE order_tracking(
    id SERIAL PRIMARY KEY,
    status order_status
);
```

```sql
INSERT INTO order_tracking(status)
VALUES('pending');
```

### Invalid Value

```sql
INSERT INTO order_tracking(status)
VALUES('pendingggggg');
```

❌ Error

```text
invalid input value for enum order_status
```

---

# 🔒 Domains

Reusable column-level constraints.

---

## Create Domain

```sql
CREATE DOMAIN positive_amount
AS NUMERIC
CHECK (VALUE > 0);
```

---

## Use Domain

```sql
CREATE TABLE payments(
    id SERIAL PRIMARY KEY,
    amount positive_amount
);
```

Valid:

```sql
INSERT INTO payments(amount)
VALUES(500);
```

Invalid:

```sql
INSERT INTO payments(amount)
VALUES(-500);
```

❌ Error

```text
value violates check constraint
```

---

# 📊 Built-in Aggregate Functions

```sql
COUNT()
SUM()
AVG()
MAX()
MIN()
```

Example:

```sql
SELECT
    COUNT(*),
    SUM(amount),
    AVG(amount)
FROM orders;
```

---

# ➕ Custom Operators

Create your own SQL operators.

---

## Function

```sql
CREATE OR REPLACE FUNCTION add_three(
    a INT,
    b INT
)
RETURNS INT
AS $$
BEGIN
    RETURN a + b + 3;
END;
$$ LANGUAGE plpgsql;
```

---

## Operator

```sql
CREATE OPERATOR #+ (
    LEFTARG = INT,
    RIGHTARG = INT,
    FUNCTION = add_three
);
```

---

## Usage

```sql
SELECT 10 #+ 20;
```

Output:

```text
33
```

---

# 🧮 Custom Aggregate Functions

---

## Step 1: State Function

```sql
CREATE OR REPLACE FUNCTION multiply_accumulator(
    state INTEGER,
    next_value INTEGER
)
RETURNS INTEGER
AS $$
BEGIN
    RETURN state * next_value;
END;
$$ LANGUAGE plpgsql;
```

---

## Step 2: Aggregate

```sql
CREATE AGGREGATE product(INTEGER) (
    SFUNC = multiply_accumulator,
    STYPE = INTEGER,
    INITCOND = '1'
);
```

---

## Test

```sql
CREATE TABLE numbers(num INT);

INSERT INTO numbers VALUES
(2),(3),(4);
```

```sql
SELECT product(num)
FROM numbers;
```

Output:

```text
24
```

---

# 🌍 Collations

Control sorting and comparison rules for text.

---

## Create English Collation

```sql
CREATE COLLATION my_english (
    PROVIDER = icu,
    LOCALE = 'en-US'
);
```

---

## Sort Using Collation

```sql
SELECT customer_name
FROM customers
ORDER BY customer_name
COLLATE my_english;
```

---

## Create Unicode Collation

```sql
CREATE COLLATION my_unicode (
    provider = icu,
    locale = 'und'
);
```

---

## Check Existing Collations

```sql
SELECT collname
FROM pg_collation;
```

```sql
SELECT collname, collprovider
FROM pg_collation;
```

---

# 🔍 Full Text Search (FTS)

PostgreSQL's built-in search engine.

---

## Inspect Components

### Configurations

```sql
SELECT cfgname
FROM pg_ts_config;
```

### Dictionaries

```sql
SELECT dictname
FROM pg_ts_dict;
```

### Parsers

```sql
SELECT prsname
FROM pg_ts_parser;
```

### Templates

```sql
SELECT tmplname
FROM pg_ts_template;
```

---

## Create Custom Configuration

```sql
CREATE TEXT SEARCH CONFIGURATION my_english
(
    COPY = english
);
```

---

## Generate Search Vector

```sql
SELECT to_tsvector(
    'my_english',
    'The cats are running'
);
```

Output:

```text
'cat':2 'run':4
```

---

## Change Dictionary Mapping

```sql
ALTER TEXT SEARCH CONFIGURATION my_english
ALTER MAPPING
FOR asciiword
WITH english_stem;
```

---

## Debug Tokenization

```sql
SELECT *
FROM ts_debug(
    'english',
    'The cats are running fast.'
);
```

---

## Search Example

```sql
SELECT
    to_tsvector(
        'english',
        'The cats are running fast'
    )
    @@
    to_tsquery(
        'english',
        'running'
    );
```

Output:

```text
true
```

### 📌 Important Operator

| Operator | Meaning |
|-----------|----------|
| `@@` | Match document against search query |

---

# 🎯 Summary

This tutorial covered PostgreSQL advanced database objects:

- 👀 Views
- ⚡ Materialized Views
- 🔢 Sequences
- 🛠 Functions
- 🚀 Procedures
- 🎯 Triggers
- 📋 ENUM Types
- 🔒 Domains
- ➕ Operators
- 🧮 Custom Aggregates
- 🌍 Collations
- 🔍 Full Text Search (FTS)

Mastering these features makes PostgreSQL much more than just a relational database—it becomes a powerful application platform capable of business logic, automation, searching, and advanced data processing directly inside the database.
