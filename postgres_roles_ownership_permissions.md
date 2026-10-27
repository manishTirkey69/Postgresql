# 🐘 PostgreSQL Roles, Ownership & Permissions

A practical guide to managing PostgreSQL users, roles, database ownership, privileges, read-only access, and security.

## 📑 Table of Contents

- [1. 👥 Understanding Roles and Users](#1--understanding-roles-and-users)
- [2. 🛠️ Creating Roles](#2--creating-roles)
- [3. 🔍 Checking Roles](#3--checking-roles)
- [4. 🏢 Understanding Database Ownership](#4--understanding-database-ownership)
- [5. 🔐 Understanding PostgreSQL Privileges](#5--understanding-postgresql-privileges)
- [6. 🎟️ Granting Permissions](#6--granting-permissions)
- [7. 🚫 Revoking Permissions](#7--revoking-permissions)
- [8. 👁️ Creating a Read-Only Role](#8--creating-a-read-only-role)
- [9. ⚙️ Default Privileges](#9--default-privileges)
- [10. 🔄 Changing Ownership](#10--changing-ownership)
- [11. 🧪 Checking Permissions](#11--checking-permissions)
- [12. 🤖 Text-to-SQL Application Example](#12--text-to-sql-application-example)
- [13. 🛡️ Security Best Practices](#13--security-best-practices)
- [14. ⚡ Quick Reference](#14--quick-reference)

---

## 1. 👥 Understanding Roles and Users

In PostgreSQL, **users and groups are both implemented using roles**.

A role can:
- 🔑 Log in to PostgreSQL.
- 🗂️ Own databases, schemas, tables, and other objects.
- 🛡️ Receive permissions on database objects.
- 👥 Inherit permissions from other roles.
- ⚙️ Have administrative attributes.

### 🔑 User vs. Role

| Term | Meaning |
|---|---|
| `ROLE` | A PostgreSQL identity that can own objects and receive privileges. |
| `LOGIN` role | A role that can authenticate and establish a database connection. |
| `NOLOGIN` role | A role typically used to group permissions. |
| `SUPERUSER` | A role with extensive administrative privileges that bypass many permission checks. |
| `OWNER` | The role that owns a database object and generally controls it. |

**Example:**

```sql
-- A role that can log in
CREATE ROLE app_user
WITH LOGIN PASSWORD 'replace_with_a_strong_password';

-- A role used to group permissions
CREATE ROLE app_readers
WITH NOLOGIN;

-- A role with database object ownership responsibilities
CREATE ROLE app_owner
WITH LOGIN PASSWORD 'replace_with_a_strong_password';

CREATE ROLE postgres WITH LOGIN SUPERUSER;
CREATE ROLE app_user WITH LOGIN PASSWORD 'strong-password';
CREATE ROLE text_to_sql_reader WITH LOGIN PASSWORD 'another-strong-password';
```

💡 **Best practice:** Use separate roles for application connections, read-only access, and database ownership.

---

## 2. 🛠️ Creating Roles

### 👤 Create a Login Role

```sql
CREATE ROLE app_user
WITH LOGIN PASSWORD 'replace_with_a_strong_password';
```

### 👥 Create a Group Role

```sql
CREATE ROLE app_readers
WITH NOLOGIN;
```

### 🔗 Add a User to a Group Role

```sql
GRANT app_readers TO app_user;
```

Depending on the role-membership options and PostgreSQL version, membership controls whether and how privileges are inherited or the role can be assumed.

### ⚙️ Common Role Attributes

| Attribute | Purpose |
|---|---|
| `LOGIN` | Allows the role to log in. |
| `NOLOGIN` | Prevents direct login. |
| `SUPERUSER` | Grants extensive administrative powers. |
| `CREATEDB` | Allows database creation. |
| `CREATEROLE` | Allows certain role-management operations. |
| `INHERIT` | Controls whether privileges from granted roles are inherited automatically. |
| `REPLICATION` | Allows replication-related connections and operations. |
| `BYPASSRLS` | Bypasses row-level security policies. |

⚠️ Avoid granting `SUPERUSER`, `CREATEDB`, `CREATEROLE`, or `BYPASSRLS` unless there is a specific operational requirement.

---

## 3. 🔍 Checking Roles

### 📋 List Roles in `psql`

```text
\du
```

### 🔎 Inspect Role Attributes Using SQL

```sql
SELECT
    rolname,
    rolsuper,
    rolinherit,
    rolcreaterole,
    rolcreatedb,
    rolcanlogin,
    rolreplication,
    rolbypassrls
FROM pg_roles
ORDER BY rolname;
```

### 👤 Check a Specific Role

```sql
SELECT *
FROM pg_roles
WHERE rolname = 'app_user';
```

### 🔐 Check Role Membership

```sql
SELECT
    member.rolname AS member_role,
    granted.rolname AS granted_role
FROM pg_auth_members AS membership
JOIN pg_roles AS member
    ON member.oid = membership.member
JOIN pg_roles AS granted
    ON granted.oid = membership.roleid
ORDER BY member.rolname, granted.rolname;
```

💡 Role membership can provide access indirectly, so checking only the privileges explicitly granted to a user may not reveal all of its effective permissions.

---

## 4. 🏢 Understanding Database Ownership

Every PostgreSQL database has an owner.

The owner generally controls the database itself, including its database-level permissions and settings. However, **database ownership does not automatically make the owner the owner of every table, view, or other object inside the database**.

### 🔎 Check Database Owners

```sql
SELECT
    datname AS database_name,
    pg_get_userbyid(datdba) AS owner
FROM pg_database
ORDER BY datname;
```

### 🔄 Change Database Ownership

```sql
ALTER DATABASE company_db OWNER TO app_owner;
```

⚠️ The executing role must have the required authority, and the new owner must satisfy PostgreSQL's ownership requirements.

### 🧠 Database vs. Schema vs. Table Ownership

| Object | What ownership means |
|---|---|
| Database | Controls the database object itself. |
| Schema | Controls the schema and its objects, subject to ownership and privilege rules. |
| Table | Controls the table and its associated privileges. |
| View | Controls the view object and its permissions. |
| Sequence | Controls the sequence object and its permissions. |

📌 **Important:** Changing a database's owner does not automatically transfer ownership of all its tables, schemas, sequences, and views.

---

## 5. 🔐 Understanding PostgreSQL Privileges

PostgreSQL uses privileges to control what roles can do.

### 🗃️ Common Database Privileges

| Privilege | Purpose |
|---|---|
| `CONNECT` | Connect to the database. |
| `CREATE` | Create schemas in the database. |
| `TEMPORARY` | Create temporary tables. |

### 📂 Common Schema Privileges

| Privilege | Purpose |
|---|---|
| `USAGE` | Access objects in the schema when the role also has the required object privileges. |
| `CREATE` | Create objects in the schema. |

### 📋 Common Table Privileges

| Privilege | Purpose |
|---|---|
| `SELECT` | Read data. |
| `INSERT` | Insert rows. |
| `UPDATE` | Update rows. |
| `DELETE` | Delete rows. |
| `TRUNCATE` | Empty a table. |
| `REFERENCES` | Create foreign-key constraints referencing a table. |
| `TRIGGER` | Create triggers on a table. |

### 🧩 Example: Permission Layers

To read a table, a role generally needs:

1. 🔌 Permission to connect to the database.
2. 📂 `USAGE` on the schema containing the table.
3. 👁️ `SELECT` on the table.

```sql
GRANT CONNECT ON DATABASE company_db TO app_readers;

GRANT USAGE ON SCHEMA public TO app_readers;

GRANT SELECT ON TABLE public.employees TO app_readers;
```

💡 Permissions at one level do not automatically grant all permissions at another level.

---

## 6. 🎟️ Granting Permissions

Use `GRANT` to assign privileges to a role.

### 🔌 Allow Database Connections

```sql
GRANT CONNECT ON DATABASE company_db TO app_user;
```

### 📂 Allow Schema Access

```sql
GRANT USAGE ON SCHEMA public TO app_user;
```

### 🆕 Allow Creating Objects in a Schema

```sql
GRANT CREATE ON SCHEMA public TO app_user;
```

⚠️ Granting `CREATE` on a schema gives the role the ability to create objects there. Do not grant it to a read-only application role.

### 👁️ Allow Reading a Table

```sql
GRANT SELECT ON TABLE public.employees TO app_readers;
```

### ✍️ Allow Modifying Table Data

```sql
GRANT INSERT, UPDATE, DELETE
ON TABLE public.employees
TO app_user;
```

### 📚 Grant Access to All Existing Tables in a Schema

```sql
GRANT SELECT
ON ALL TABLES IN SCHEMA public
TO app_readers;
```

This applies to existing tables and views in the specified schema.

### 🔢 Grant Sequence Access

Some tables use sequences to generate IDs.

```sql
GRANT USAGE, SELECT
ON ALL SEQUENCES IN SCHEMA public
TO app_user;
```

### 🗂️ Grant Access to All Existing Tables and Sequences

```sql
GRANT SELECT
ON ALL TABLES IN SCHEMA public
TO app_readers;

GRANT USAGE, SELECT
ON ALL SEQUENCES IN SCHEMA public
TO app_readers;
```

📌 **Remember:** These commands affect existing objects. Objects created later require separate grants or suitable default privileges.

---

## 7. 🚫 Revoking Permissions

Use `REVOKE` to remove previously granted privileges.

### ❌ Remove Table Read Access

```sql
REVOKE SELECT
ON TABLE public.employees
FROM app_readers;
```

### ❌ Remove Schema Access

```sql
REVOKE USAGE
ON SCHEMA public
FROM app_readers;
```

### ❌ Remove Database Connection Access

```sql
REVOKE CONNECT
ON DATABASE company_db
FROM app_user;
```

### ❌ Remove Multiple Table Privileges

```sql
REVOKE INSERT, UPDATE, DELETE
ON TABLE public.employees
FROM app_user;
```

### ⚠️ Important: Revoking a Grant May Not Remove All Effective Access

A role might still have access through:
- 👥 Membership in another role.
- 🌍 Privileges granted to `PUBLIC`.
- 🔑 Another direct grant.
- 🏢 Ownership of the object.
- 🛡️ Administrative privileges.

Always inspect the role's effective permissions after changing grants.

---

## 8. 👁️ Creating a Read-Only Role

A read-only role is useful for reporting tools, analytics, dashboards, and Text-to-SQL applications.

### Step 1️⃣: Create the Role

```sql
CREATE ROLE text_to_sql_reader
WITH LOGIN PASSWORD 'replace_with_a_strong_password';
```

### Step 2️⃣: Grant Database Connection Access

```sql
GRANT CONNECT
ON DATABASE company_db
TO text_to_sql_reader;
```

### Step 3️⃣: Grant Schema Access

```sql
GRANT USAGE
ON SCHEMA public
TO text_to_sql_reader;
```

### Step 4️⃣: Grant Read Access to Existing Tables

```sql
GRANT SELECT
ON ALL TABLES IN SCHEMA public
TO text_to_sql_reader;
```

### Step 5️⃣: Grant Read Access to Existing Sequences, If Needed

```sql
GRANT SELECT
ON ALL SEQUENCES IN SCHEMA public
TO text_to_sql_reader;
```

Sequence access is generally unnecessary for ordinary table-reading queries, so grant it only if the application needs it.

### Step 6️⃣: Verify the Permissions

```sql
SELECT
    has_database_privilege(
        'text_to_sql_reader',
        'company_db',
        'CONNECT'
    ) AS can_connect,

    has_schema_privilege(
        'text_to_sql_reader',
        'public',
        'USAGE'
    ) AS can_use_schema,

    has_table_privilege(
        'text_to_sql_reader',
        'public.employees',
        'SELECT'
    ) AS can_read_employees;
```

### 🧪 Test the Role

Connect as `text_to_sql_reader` and try a read query:

```sql
SELECT *
FROM public.employees
LIMIT 10;
```

Then try a write query:

```sql
DELETE FROM public.employees;
```

The write should fail if the role has no effective `DELETE` privilege and is not the owner or otherwise privileged to perform the operation.

⚠️ **Security note:** A role is not truly read-only merely because you have not granted it write access directly. Verify inherited roles, ownership, `PUBLIC` grants, callable functions, and other effective privileges.

---

## 9. ⚙️ Default Privileges

One common PostgreSQL permissions problem is that **new tables do not automatically receive the same grants as existing tables**.

For example, suppose you run:

```sql
GRANT SELECT
ON ALL TABLES IN SCHEMA public
TO text_to_sql_reader;
```

This grants access to existing tables. It does not automatically grant access to tables created later.

### 🛠️ Set Default Privileges for Future Tables

```sql
ALTER DEFAULT PRIVILEGES
FOR ROLE app_owner
IN SCHEMA public
GRANT SELECT ON TABLES TO text_to_sql_reader;
```

### 🔢 Set Default Privileges for Future Sequences

```sql
ALTER DEFAULT PRIVILEGES
FOR ROLE app_owner
IN SCHEMA public
GRANT USAGE, SELECT ON SEQUENCES TO text_to_sql_reader;
```

### 🧠 How Default Privileges Work

Default privileges apply to objects created by the specified role. They are not a universal setting for every user who creates an object in that schema.

For example:

```sql
ALTER DEFAULT PRIVILEGES
FOR ROLE app_owner
IN SCHEMA public
GRANT SELECT ON TABLES TO text_to_sql_reader;
```

This affects future tables created by `app_owner` in `public`.

If another role creates a table, the default privileges configured for `app_owner` do not automatically apply to that table.

📌 **Best practice:** Decide which role will create and own application objects, then configure default privileges for that role.

---

## 10. 🔄 Changing Ownership

Ownership determines who controls an object. It is different from receiving a privilege such as `SELECT`.

### 🗄️ Change Database Ownership

```sql
ALTER DATABASE company_db OWNER TO app_owner;
```

### 📂 Change Schema Ownership

```sql
ALTER SCHEMA public OWNER TO app_owner;
```

⚠️ Changing ownership of the built-in `public` schema may affect existing applications and deployments. Review the implications before doing this in a production database.

### 📋 Change Table Ownership

```sql
ALTER TABLE public.employees OWNER TO app_owner;
```

### 🔢 Change Sequence Ownership

```sql
ALTER SEQUENCE public.employees_id_seq OWNER TO app_owner;
```

### 🔍 Find Table Owners

```sql
SELECT
    schemaname,
    tablename,
    tableowner
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
```

### 📚 Find Sequence Owners

```sql
SELECT
    sequence_schema,
    sequence_name,
    sequence_owner
FROM information_schema.sequences
WHERE sequence_schema = 'public'
ORDER BY sequence_name;
```

### 🧠 Ownership vs. Permissions

| Operation | Purpose |
|---|---|
| `ALTER DATABASE ... OWNER TO ...` | Changes the database owner. |
| `ALTER TABLE ... OWNER TO ...` | Changes the table owner. |
| `GRANT SELECT ...` | Allows reading a table without transferring ownership. |
| `REVOKE SELECT ...` | Removes a particular read grant, subject to other effective privileges. |

💡 **Important:** You do not need to transfer ownership just to allow a role to read or modify table data. Use `GRANT` for that purpose.

---

## 11. 🧪 Checking Permissions

When a user reports that they cannot read a table, inspect each permission layer.

### 🔌 Check Database Connection Access

```sql
SELECT has_database_privilege(
    'app_user',
    'company_db',
    'CONNECT'
);
```

### 📂 Check Schema Access

```sql
SELECT has_schema_privilege(
    'app_user',
    'public',
    'USAGE'
);
```

### 👁️ Check Table Read Access

```sql
SELECT has_table_privilege(
    'app_user',
    'public.employees',
    'SELECT'
);
```

### ✍️ Check Table Write Access

```sql
SELECT
    has_table_privilege(
        'app_user',
        'public.employees',
        'INSERT'
    ) AS can_insert,

    has_table_privilege(
        'app_user',
        'public.employees',
        'UPDATE'
    ) AS can_update,

    has_table_privilege(
        'app_user',
        'public.employees',
        'DELETE'
    ) AS can_delete;
```

### 📋 Inspect Explicit Table Grants

```sql
SELECT
    grantee,
    table_schema,
    table_name,
    privilege_type,
    is_grantable
FROM information_schema.role_table_grants
WHERE table_schema = 'public'
ORDER BY table_name, grantee, privilege_type;
```

### 🔎 Inspect Schema Privileges

```sql
SELECT
    grantee,
    schema_name,
    privilege_type
FROM information_schema.schema_privileges
WHERE schema_name = 'public'
ORDER BY grantee, privilege_type;
```

If `information_schema.schema_privileges` is unavailable in your PostgreSQL environment, inspect schema privileges through the `information_schema` views available in your version or use `has_schema_privilege()`.

### 🚨 Troubleshooting Checklist

If a query fails with `permission denied`, check:

- 🔌 Does the role have `CONNECT` on the database?
- 📂 Does the role have `USAGE` on the schema?
- 👁️ Does it have the required table or view privilege?
- 👥 Does it inherit privileges from another role?
- 🌍 Are there grants to `PUBLIC`?
- 🔢 Does the query access a sequence?
- ⚙️ Does the query call a function requiring additional permissions?
- 🛡️ Does row-level security restrict which rows are visible?
- 🔑 Is the application connecting as the role you expect?

---

## 12. 🤖 Text-to-SQL Application Example

A Text-to-SQL application converts natural-language questions into SQL queries.

Example:

> 💬 "Show the 10 employees with the highest salaries."

An LLM might generate:

```sql
SELECT name, salary
FROM public.employees
ORDER BY salary DESC
LIMIT 10;
```

The application should validate the generated query and execute it using a dedicated, restricted database role.

### 🏗️ Recommended Architecture

```text
👤 User
   |
   v
💬 Natural-language question
   |
   v
🤖 LLM generates SQL
   |
   v
🛡️ SQL validation and policy checks
   |
   v
🔌 Read-only PostgreSQL connection
   |
   v
📊 Query results
   |
   v
💬 Response to user
```

### 🔐 Security Requirements

- Use a dedicated database role with minimal privileges.
- Allow only approved read operations.
- Reject multiple statements unless explicitly required and safely supported.
- Use an SQL parser or AST-based validator rather than relying only on regular expressions.
- Apply statement timeouts and result-size limits.
- Restrict access to sensitive tables and columns.
- Avoid exposing database credentials to the LLM.
- Log query metadata safely without unnecessarily recording sensitive information.

### 🐍 Python Example Using SQLAlchemy

Install the dependency:

```bash
pip install sqlalchemy psycopg
```

Set a database URL in an environment variable:

```bash
export DATABASE_URL="postgresql+psycopg://text_to_sql_reader:YOUR_PASSWORD@localhost:5432/company_db"
```

Example:

```python
import os

from sqlalchemy import create_engine, text

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=0,
)

def execute_read_query(sql: str):
    """
    Example of executing a query in a read-only transaction.

    Production applications must validate the SQL before execution.
    The database role must also have appropriately restricted privileges.
    """

    with engine.begin() as connection:
        connection.execute(text("SET TRANSACTION READ ONLY"))

        connection.execute(
            text("SET LOCAL statement_timeout = '5s'")
        )

        result = connection.execute(text(sql))

        return [dict(row) for row in result.mappings().fetchmany(100)]
```

⚠️ **Important:** This is a demonstration, not a complete SQL security validator. Do not pass arbitrary user-generated SQL directly into this function. Validate the SQL before execution, restrict accessible objects through database permissions, and enforce appropriate row and execution limits.

The database-level read-only role remains essential even when the application validates queries.

---

## 13. 🛡️ Security Best Practices

### 🔑 1. Follow the Principle of Least Privilege

Grant only the permissions required for a role's job.

```sql
GRANT CONNECT ON DATABASE company_db TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT ON TABLE public.employees TO app_user;
```

Avoid granting broad access when table-specific privileges are sufficient.

### 🚫 2. Avoid Using Superuser Accounts in Applications

Do not connect your web application or AI agent as a PostgreSQL superuser.

```sql
-- Avoid using a superuser for routine application queries.
```

Use a dedicated application role instead.

### 🔐 3. Use Strong Credentials

- Store credentials in environment variables or a secrets manager.
- Do not commit passwords to Git.
- Rotate credentials according to your security requirements.
- Avoid reusing passwords across services.

### 👥 4. Separate Roles by Responsibility

A practical setup might include:

| Role | Responsibility |
|---|---|
| `app_owner` | Owns application database objects. |
| `app_user` | Performs the application's required operations. |
| `app_readers` | Provides shared read permissions. |
| `text_to_sql_reader` | Reads approved data for AI-generated queries. |
| `db_admin` | Performs authorized database administration. |

These are example names, not predefined PostgreSQL roles.

### 🌍 5. Review `PUBLIC` Permissions

In PostgreSQL, `PUBLIC` represents all roles.

Review the grants that apply to `PUBLIC` and revoke unnecessary access when appropriate. Be careful: changing default permissions or privileges on a shared database can affect existing applications.

### 🧱 6. Use Schema Separation

For sensitive applications, separate data into schemas and grant access only to the required schemas.

For example:

```sql
CREATE SCHEMA reporting;

GRANT USAGE ON SCHEMA reporting TO text_to_sql_reader;

GRANT SELECT
ON ALL TABLES IN SCHEMA reporting
TO text_to_sql_reader;
```

### 🛡️ 7. Consider Row-Level Security

Row-level security (RLS) can restrict which rows a role can access.

```sql
ALTER TABLE public.employees
ENABLE ROW LEVEL SECURITY;
```

Policies must also be configured. Enabling RLS alone does not define which rows are accessible.

⚠️ Table owners generally bypass row-level security unless it is forced, and superusers and roles with `BYPASSRLS` can bypass it. Design and test policies carefully.

### 🧪 8. Test Permissions as the Actual Application Role

A permission check performed by an administrator does not prove that the application role has the same access.

Connect using the application role and test the intended operations.

### 📜 9. Audit Permission Changes

Review grants and role memberships periodically, especially after changes to application architecture or employee responsibilities.

### 🤖 10. Apply Extra Controls to AI Agents

For Text-to-SQL or autonomous agents:

- Use a dedicated restricted role.
- Allowlist schemas, tables, and columns.
- Enforce query timeouts and result limits.
- Block write operations when they are not required.
- Prevent access to secrets and sensitive system tables.
- Treat generated SQL as untrusted input.
- Use database permissions as a final enforcement layer.

---

## 14. ⚡ Quick Reference

| Task | SQL Command |
|---|---|
| 👤 Create a login role | `CREATE ROLE app_user WITH LOGIN PASSWORD 'strong_password';` |
| 👥 Create a group role | `CREATE ROLE app_readers WITH NOLOGIN;` |
| 🔗 Grant role membership | `GRANT app_readers TO app_user;` |
| 🔌 Allow database connections | `GRANT CONNECT ON DATABASE company_db TO app_user;` |
| 📂 Allow schema access | `GRANT USAGE ON SCHEMA public TO app_user;` |
| 👁️ Grant table read access | `GRANT SELECT ON TABLE public.employees TO app_user;` |
| ✍️ Grant write access | `GRANT INSERT, UPDATE, DELETE ON TABLE public.employees TO app_user;` |
| 🚫 Remove read access | `REVOKE SELECT ON TABLE public.employees FROM app_user;` |
| 🏢 Change database owner | `ALTER DATABASE company_db OWNER TO app_owner;` |
| 📋 Change table owner | `ALTER TABLE public.employees OWNER TO app_owner;` |
| 🔍 Check table read access | `SELECT has_table_privilege('app_user', 'public.employees', 'SELECT');` |
| ⚙️ Set default table privileges | `ALTER DEFAULT PRIVILEGES FOR ROLE app_owner IN SCHEMA public GRANT SELECT ON TABLES TO text_to_sql_reader;` |

---

## 🎯 Key Takeaways

- 👥 **Roles** represent users and permission groups.
- 🏢 **Ownership** determines control over a database object.
- 🔐 **Privileges** determine which operations a role can perform.
- 📂 **Schema access** and table privileges are separate permission layers.
- ⚙️ **Default privileges** apply to future objects created by the configured role.
- 👁️ **Read-only roles** are useful for reporting, analytics, and Text-to-SQL systems.
- 🛡️ **Least privilege** reduces the risk of accidental or unauthorized changes.
- 🤖 **AI-generated SQL must be treated as untrusted input** and protected with application validation and database-level restrictions.

**The most important rule:** Grant the minimum permissions required, verify effective access, and test using the actual application role.
