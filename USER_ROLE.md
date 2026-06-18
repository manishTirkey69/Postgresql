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
