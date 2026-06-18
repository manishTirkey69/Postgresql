# 📡 PostgreSQL Logical Replication
## Publication & Subscription Guide

> Learn how PostgreSQL Logical Replication works using **Publication** and **Subscription**.

---

## 🏷️ Tags

`postgresql` `logical-replication` `publication` `subscription` `cdc`
`database` `wal` `replication-slot` `pgoutput`
`streaming-data` `event-driven-architecture`

---

# 📖 Table of Contents

- [What is Logical Replication?](#-what-is-logical-replication)
- [Architecture](#-architecture)
- [Prerequisites](#-prerequisites)
- [Publisher Setup](#-publisher-setup)
- [Subscriber Setup](#-subscriber-setup)
- [Creating a Publication](#-creating-a-publication)
- [Creating a Subscription](#-creating-a-subscription)
- [Testing Replication](#-testing-replication)
- [Monitoring Replication](#-monitoring-replication)
- [Replication Slots](#-replication-slots)
- [How It Works Internally](#-how-it-works-internally)
- [Advantages](#-advantages)
- [Limitations](#-limitations)
- [Real World Use Cases](#-real-world-use-cases)

---

# 📡 What is Logical Replication?

Logical Replication allows PostgreSQL to replicate data changes from one database to another.

Instead of copying physical database files, PostgreSQL sends logical changes such as:

- ✅ INSERT
- ✅ UPDATE
- ✅ DELETE
- ✅ TRUNCATE

This is achieved through:

- **Publication** → Defines what data to publish.
- **Subscription** → Defines who receives published changes.

---

# 🏗️ Architecture

```text
Publisher Database
       │
       ▼
   WAL Records
       │
       ▼
Logical Decoding
       │
       ▼
  Publication
       │
       ▼
Replication Slot
       │
       ▼
 Subscription
       │
       ▼
Subscriber Database
```

---

# 🎯 Example Environment

```text
Publisher (Docker PostgreSQL)
Host : localhost
Port : 5433

Subscriber (Local PostgreSQL)
Host : localhost
Port : 5432
```

---

# 📋 Prerequisites

The Publisher must have:

```sql
SHOW wal_level;
SHOW max_replication_slots;
SHOW max_wal_senders;
```

Expected:

```text
wal_level             = logical
max_replication_slots = 10
max_wal_senders       = 10
```

---

# 🖥️ Publisher Setup

## Step 1: Create Replication User

```sql
CREATE ROLE replicator
WITH
LOGIN
REPLICATION
PASSWORD 'secret123';
```

Verify:

```sql
SELECT rolname, rolreplication
FROM pg_roles;
```

---

## Step 2: Create Database

```sql
CREATE DATABASE publisher_db;
```

Connect:

```sql
\c publisher_db
```

---

## Step 3: Create Table

```sql
CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    name TEXT,
    salary NUMERIC
);
```

Insert sample data:

```sql
INSERT INTO employees(name, salary)
VALUES
('Manish', 50000),
('Rahul', 60000);
```

---

# 📤 Creating a Publication

Create a publication for the employees table:

```sql
CREATE PUBLICATION emp_pub
FOR TABLE employees;
```

Verify:

```sql
SELECT *
FROM pg_publication;
```

---

## Publish Multiple Tables

```sql
CREATE PUBLICATION app_pub
FOR TABLE
employees,
departments,
projects;
```

---

## Publish All Tables

```sql
CREATE PUBLICATION app_pub
FOR ALL TABLES;
```

---

# 🖥️ Subscriber Setup

## Step 1: Create Database

```sql
CREATE DATABASE subscriber_db;
```

Connect:

```sql
\c subscriber_db
```

---

## Step 2: Create Matching Table Structure

⚠️ PostgreSQL does NOT automatically create tables.

Schema must already exist.

```sql
CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    name TEXT,
    salary NUMERIC
);
```

---

# 📥 Creating a Subscription

```sql
CREATE SUBSCRIPTION emp_sub
CONNECTION '
host=localhost
port=5433
dbname=publisher_db
user=replicator
password=secret123
'
PUBLICATION emp_pub;
```

---

# 🧪 Testing Replication

## Insert

Publisher:

```sql
INSERT INTO employees(name,salary)
VALUES ('Amit',70000);
```

Subscriber:

```sql
SELECT * FROM employees;
```

Result:

```text
1 | Manish | 50000
2 | Rahul  | 60000
3 | Amit   | 70000
```

---

## Update

Publisher:

```sql
UPDATE employees
SET salary = 90000
WHERE id = 1;
```

Subscriber automatically receives:

```text
1 | Manish | 90000
```

---

## Delete

Publisher:

```sql
DELETE
FROM employees
WHERE id = 2;
```

Subscriber:

```text
Row Removed
```

---

# 🔍 Monitoring Replication

## View Publications

```sql
SELECT *
FROM pg_publication;
```

---

## View Subscriptions

```sql
SELECT *
FROM pg_subscription;
```

---

## Subscriber Status

```sql
SELECT *
FROM pg_stat_subscription;
```

Expected:

```text
streaming
```

---

## Publisher Status

```sql
SELECT *
FROM pg_stat_replication;
```

Shows active subscribers connected to the publisher.

---

# 🎟️ Replication Slots

Every subscription creates a replication slot on the publisher.

View slots:

```sql
SELECT *
FROM pg_replication_slots;
```

Example:

```text
slot_name : emp_sub
active    : true
```

---

## Why Replication Slots?

Replication slots ensure WAL files are not deleted before subscribers consume them.

Without slots:

```text
WAL Removed
Subscriber Misses Data
❌ Replication Breaks
```

With slots:

```text
WAL Retained
Subscriber Receives Data
✅ Replication Continues
```

---

# ⚙️ How It Works Internally

When an INSERT occurs:

```sql
INSERT INTO employees
VALUES (...);
```

PostgreSQL writes:

```text
WAL Record
```

Example Flow:

```text
INSERT
  │
  ▼
WAL
  │
  ▼
Logical Decoding
  │
  ▼
Publication
  │
  ▼
Replication Slot
  │
  ▼
Subscription
  │
  ▼
Subscriber Table
```

---

# 🚀 Advantages

### Near Real-Time Replication

Changes appear almost instantly.

### Selective Replication

Replicate only required tables.

### Cross-Version Support

Different PostgreSQL versions can replicate logically.

### Data Distribution

Send data to multiple databases.

### CDC Foundation

Used by tools like:

- Debezium
- Kafka Connect
- Airbyte
- Fivetran

---

# ⚠️ Limitations

## Replicated

- ✅ INSERT
- ✅ UPDATE
- ✅ DELETE
- ✅ TRUNCATE

## Not Replicated

- ❌ CREATE TABLE
- ❌ ALTER TABLE
- ❌ DROP TABLE
- ❌ CREATE INDEX
- ❌ ROLE Changes

Schema changes must be applied manually.

---

# 🌎 Real World Use Cases

## Reporting Database

```text
Production DB
      │
      ▼
Reporting DB
```

Run analytics without affecting production.

---

## Event Streaming

```text
PostgreSQL
     │
     ▼
Debezium
     │
     ▼
Kafka
```

Capture every database change as an event.

---

## Microservices

```text
Orders DB
     │
     ▼
Billing DB

Inventory DB

Analytics DB
```

Share selected tables between services.

---

## Data Warehouse Sync

```text
PostgreSQL
     │
     ▼
Snowflake

BigQuery

Redshift
```

---

# 🧠 Key Concepts Summary

| Concept | Purpose |
|----------|----------|
| WAL | Stores database changes |
| Logical Decoding | Converts WAL to readable changes |
| Publication | Defines what to publish |
| Subscription | Receives published changes |
| Replication Slot | Tracks subscriber progress |
| Publisher | Source database |
| Subscriber | Target database |

---

# 🎯 Quick Commands Cheat Sheet

```sql
-- Publications
SELECT * FROM pg_publication;

-- Subscriptions
SELECT * FROM pg_subscription;

-- Subscriber Status
SELECT * FROM pg_stat_subscription;

-- Publisher Status
SELECT * FROM pg_stat_replication;

-- Replication Slots
SELECT * FROM pg_replication_slots;

-- Create Publication
CREATE PUBLICATION emp_pub
FOR TABLE employees;

-- Create Subscription
CREATE SUBSCRIPTION emp_sub
CONNECTION '...'
PUBLICATION emp_pub;
```

---

## 📚 Next Topics

After mastering Publication & Subscription:

1. WAL Internals
2. Replication Slots Deep Dive
3. Logical Decoding
4. pgoutput Plugin
5. wal2json Plugin
6. Change Data Capture (CDC)
7. Debezium Integration
8. Kafka + PostgreSQL
9. Streaming Architectures
10. High Availability Replication
11. Physical Replication
12. PostgreSQL Failover Str
