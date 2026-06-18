# 🔐 PostgreSQL Read-Only User Role

![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Security-blue)
![Role](https://img.shields.io/badge/Role-Read--Only-green)
![Database](https://img.shields.io/badge/Database-Access_Control-orange)

## 📖 Overview

This guide demonstrates how to create a dedicated **read-only PostgreSQL user** that can:

- ✅ Connect to a database
- ✅ Access a schema
- ✅ Read data from existing tables
- ✅ Automatically read future tables
- ❌ Cannot INSERT data
- ❌ Cannot UPDATE data
- ❌ Cannot DELETE data
- ❌ Cannot CREATE tables

This type of role is commonly used for:

- 🤖 AI Agents
- 📊 Reporting Dashboards
- 📈 BI Tools
- 🔍 Analytics Users
- 📋 Audit Systems
- 🛡 Security-focused Applications

---

# 🏗 Step 1: Create the Role

Create a login-enabled role.

```sql
CREATE ROLE ai_agent_readonly
LOGIN
PASSWORD 'strong_password';
```

### Explanation

| Option | Meaning |
|----------|----------|
| `CREATE ROLE` | Creates a PostgreSQL role |
| `LOGIN` | Allows the role to connect to PostgreSQL |
| `PASSWORD` | Authentication password |

---

# 🔌 Step 2: Allow Database Connection

Grant permission to connect to the target database.

```sql
GRANT CONNECT
ON DATABASE "Learning_db"
TO ai_agent_readonly;
```

### Why?

Without `CONNECT`, the user cannot access the database even if other permissions exist.

```text
Role
  │
  ▼
CONNECT
  │
  ▼
Database Access
```

---

# 📂 Step 3: Grant Schema Access

Allow the role to access objects inside the schema.

```sql
GRANT USAGE
ON SCHEMA public
TO ai_agent_readonly;
```

### Why?

Schemas act like folders.

Without `USAGE`, PostgreSQL blocks access to tables even when SELECT permission exists.

```text
Database
│
└── public schema
      │
      ├── customers
      ├── orders
      └── products
```

---

# 📖 Step 4: Grant Read Access to Existing Tables

Provide SELECT access on all current tables.

```sql
GRANT SELECT
ON ALL TABLES IN SCHEMA public
TO ai_agent_readonly;
```

### Result

The role can execute:

```sql
SELECT * FROM customers;

SELECT * FROM orders;

SELECT * FROM products;
```

But cannot execute:

```sql
INSERT INTO customers VALUES (...);

UPDATE customers
SET city = 'Ranchi';

DELETE FROM customers;
```

---

# 🔄 Step 5: Grant Access to Future Tables

When new tables are created, the role would normally lose access.

Configure default privileges:

```sql
ALTER DEFAULT PRIVILEGES
IN SCHEMA public
GRANT SELECT ON TABLES
TO ai_agent_readonly;
```

### Why?

Without this command:

```sql
CREATE TABLE invoices (...);
```

The role would not automatically gain access.

With default privileges enabled:

```sql
CREATE TABLE invoices (...);
```

✅ `ai_agent_readonly` can immediately query the new table.

---

# 🚀 Complete Script

```sql
CREATE ROLE ai_agent_readonly
LOGIN
PASSWORD 'strong_password';

GRANT CONNECT
ON DATABASE "Learning_db"
TO ai_agent_readonly;

GRANT USAGE
ON SCHEMA public
TO ai_agent_readonly;

GRANT SELECT
ON ALL TABLES IN SCHEMA public
TO ai_agent_readonly;

ALTER DEFAULT PRIVILEGES
IN SCHEMA public
GRANT SELECT ON TABLES
TO ai_agent_readonly;
```

---

# 🧪 Testing the Role

Login as the read-only user:

```bash
psql -U ai_agent_readonly -d Learning_db
```

Run:

```sql
SELECT * FROM customers;
```

✅ Works

```sql
INSERT INTO customers
VALUES (1,'Manish');
```

❌ Permission Denied

```sql
UPDATE customers
SET city='Ranchi';
```

❌ Permission Denied

```sql
DELETE FROM customers;
```

❌ Permission Denied

---

# 🔍 Verify Role Permissions

View role information:

```sql
SELECT
    rolname,
    rolcanlogin
FROM pg_roles
WHERE rolname = 'ai_agent_readonly';
```

Check table privileges:

```sql
SELECT *
FROM information_schema.role_table_grants
WHERE grantee = 'ai_agent_readonly';
```

---

# 🛡 Production Best Practices

### Use Strong Passwords

```sql
PASSWORD 'VeryStrongPassword@123';
```

---

### Prefer Dedicated Roles

Good:

```text
ai_agent_readonly
dashboard_user
reporting_user
analytics_user
```

Avoid:

```text
postgres
admin
superuser
```

---

### Follow Principle of Least Privilege

Grant only what is necessary.

```text
CONNECT  ✅
USAGE    ✅
SELECT   ✅

INSERT   ❌
UPDATE   ❌
DELETE   ❌
CREATE   ❌
DROP     ❌
```

---

# 🎯 Summary

This setup creates a secure read-only PostgreSQL account that can:

- ✅ Login to PostgreSQL
- ✅ Connect to `Learning_db`
- ✅ Access the `public` schema
- ✅ Read existing tables
- ✅ Read future tables automatically
- ❌ Modify data
- ❌ Delete data
- ❌ Create objects

Perfect for AI agents, dashboards, reporting tools, analytics systems, and external consumers that only require read access.








# 🐍 PostgreSQL Read-Only Role Automation with Python

![Python](https://img.shields.io/badge/Python-3.x-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Role_Management-blue)
![psycopg2](https://img.shields.io/badge/psycopg2-Database_Driver-green)

## 📖 Overview

This Python script automatically creates and configures a PostgreSQL **read-only role**.

The script performs the following tasks:

- ✅ Connects to PostgreSQL using a superuser account
- ✅ Checks whether the role already exists
- ✅ Creates the role if missing
- ✅ Grants database connection permissions
- ✅ Grants schema access permissions
- ✅ Grants SELECT access on existing tables
- ✅ Grants SELECT access on future tables
- ✅ Prevents duplicate role creation

This is useful for:

- 🤖 AI Agents
- 📊 Reporting Dashboards
- 📈 Analytics Tools
- 🔍 Read-Only Applications
- 🛡 Audit Systems

---

# 📦 Requirements

Install psycopg2:

```bash
pip install psycopg2-binary
```

Verify installation:

```bash
python -c "import psycopg2; print(psycopg2.__version__)"
```

---

# ⚙️ Configuration

Update the database connection settings before running the script.

```python
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "postgres",
    "user": "postgres",
    "password": "your_password",
}
```

### Configuration Parameters

| Parameter | Description |
|------------|------------|
| `host` | PostgreSQL server hostname |
| `port` | PostgreSQL server port |
| `dbname` | Administrative database used for connection |
| `user` | PostgreSQL superuser |
| `password` | PostgreSQL password |

---

## Role Configuration

```python
ROLE_NAME = "ai_agent_readonly"
ROLE_PASSWORD = "strong_password"
TARGET_DB = "Learning_db"
TARGET_SCHEMA = "public"
```

| Variable | Purpose |
|-----------|----------|
| `ROLE_NAME` | Read-only role name |
| `ROLE_PASSWORD` | Login password |
| `TARGET_DB` | Database to access |
| `TARGET_SCHEMA` | Schema containing tables |

---

# 🔄 Script Workflow

```text
Start
  │
  ▼
Connect to PostgreSQL
  │
  ▼
Check if Role Exists
  │
  ├── Yes
  │      │
  │      ▼
  │  Skip Creation
  │
  └── No
         │
         ▼
     Create Role
         │
         ▼
Grant CONNECT
         │
         ▼
Grant USAGE
         │
         ▼
Grant SELECT on Existing Tables
         │
         ▼
Grant SELECT on Future Tables
         │
         ▼
Done
```

---

# 🛠 Complete Script

```python
import psycopg2
from psycopg2 import sql

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "postgres",
    "user": "postgres",
    "password": "your_password",
}

ROLE_NAME = "ai_agent_readonly"
ROLE_PASSWORD = "strong_password"
TARGET_DB = "Learning_db"
TARGET_SCHEMA = "public"


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True

    try:
        with conn.cursor() as cur:

            # Check if role exists
            cur.execute(
                """
                SELECT 1
                FROM pg_roles
                WHERE rolname = %s
                """,
                (ROLE_NAME,),
            )

            if cur.fetchone() is None:
                cur.execute(
                    sql.SQL(
                        """
                        CREATE ROLE {}
                        LOGIN
                        PASSWORD %s
                        """
                    ).format(sql.Identifier(ROLE_NAME)),
                    (ROLE_PASSWORD,),
                )
                print(f"Created role: {ROLE_NAME}")
            else:
                print(f"Role already exists: {ROLE_NAME}")

            # Grant database connection
            cur.execute(
                sql.SQL(
                    """
                    GRANT CONNECT
                    ON DATABASE {}
                    TO {}
                    """
                ).format(
                    sql.Identifier(TARGET_DB),
                    sql.Identifier(ROLE_NAME),
                )
            )

            # Grant schema access
            cur.execute(
                sql.SQL(
                    """
                    GRANT USAGE
                    ON SCHEMA {}
                    TO {}
                    """
                ).format(
                    sql.Identifier(TARGET_SCHEMA),
                    sql.Identifier(ROLE_NAME),
                )
            )

            # Grant SELECT on existing tables
            cur.execute(
                sql.SQL(
                    """
                    GRANT SELECT
                    ON ALL TABLES IN SCHEMA {}
                    TO {}
                    """
                ).format(
                    sql.Identifier(TARGET_SCHEMA),
                    sql.Identifier(ROLE_NAME),
                )
            )

            # Grant SELECT on future tables
            cur.execute(
                sql.SQL(
                    """
                    ALTER DEFAULT PRIVILEGES
                    IN SCHEMA {}
                    GRANT SELECT ON TABLES
                    TO {}
                    """
                ).format(
                    sql.Identifier(TARGET_SCHEMA),
                    sql.Identifier(ROLE_NAME),
                )
            )

            print("Permissions granted successfully.")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
```

---

# 🔍 What Each Permission Does

## CONNECT

```sql
GRANT CONNECT
ON DATABASE Learning_db
TO ai_agent_readonly;
```

Allows:

```text
Login → Database
```

Without it:

```text
❌ Cannot connect to database
```

---

## USAGE

```sql
GRANT USAGE
ON SCHEMA public
TO ai_agent_readonly;
```

Allows access to schema objects.

Without it:

```text
❌ Tables exist
❌ SELECT still fails
```

---

## SELECT on Existing Tables

```sql
GRANT SELECT
ON ALL TABLES IN SCHEMA public
TO ai_agent_readonly;
```

Allows:

```sql
SELECT * FROM customers;
SELECT * FROM orders;
```

Prevents:

```sql
INSERT ...
UPDATE ...
DELETE ...
```

---

## SELECT on Future Tables

```sql
ALTER DEFAULT PRIVILEGES
IN SCHEMA public
GRANT SELECT ON TABLES
TO ai_agent_readonly;
```

Ensures newly created tables automatically inherit read permissions.

Example:

```sql
CREATE TABLE invoices (...);
```

Immediately accessible by:

```sql
SELECT * FROM invoices;
```

---

# ▶️ Running the Script

Execute:

```bash
python create_readonly_role.py
```

Expected output:

```text
Created role: ai_agent_readonly
Permissions granted successfully.
```

Or:

```text
Role already exists: ai_agent_readonly
Permissions granted successfully.
```

---

# 🧪 Verify in PostgreSQL

Check role:

```sql
SELECT
    rolname,
    rolcanlogin
FROM pg_roles
WHERE rolname = 'ai_agent_readonly';
```

---

Check grants:

```sql
SELECT *
FROM information_schema.role_table_grants
WHERE grantee = 'ai_agent_readonly';
```

---

# 🔐 Security Best Practices

### Use Environment Variables

Avoid storing passwords directly in source code.

```python
import os

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}
```

---

### Use Strong Passwords

```text
Weak:
123456

Strong:
A!_Agent#2026$Secure
```

---

### Grant Minimum Permissions

Recommended:

```text
CONNECT  ✅
USAGE    ✅
SELECT   ✅

INSERT   ❌
UPDATE   ❌
DELETE   ❌
DROP     ❌
CREATE   ❌
```

---

# 🎯 Summary

This script automates PostgreSQL read-only role creation and permission management.

After execution, the role can:

- ✅ Login to PostgreSQL
- ✅ Connect to `Learning_db`
- ✅ Access the `public` schema
- ✅ Read all current tables
- ✅ Read all future tables
- ❌ Insert records
- ❌ Update records
- ❌ Delete records
- ❌ Create database objects

Ideal for AI agents, reporting tools, dashboards, analytics systems, and external consumers requiring safe read-only access
