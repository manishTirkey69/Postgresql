# 🐘 PostgreSQL Replication: Same Server vs Different Server

A practical guide to creating PostgreSQL replicas, synchronizing database changes, configuring replication, and monitoring replication health.

## 📑 Table of Contents

- [1. 🎯 What Is Database Replication?](#1--what-is-database-replication)
- [2. 🧠 PostgreSQL Replication Types](#2--postgresql-replication-types)
- [3. 🖥️ Replication on the Same Server](#3-️-replication-on-the-same-server)
- [4. 🌐 Replication on Different Servers](#4--replication-on-different-servers)
- [5. 🔄 Physical vs Logical Replication](#5--physical-vs-logical-replication)
- [6. 👁️ Reading Data from a Replica](#6-️-reading-data-from-a-replica)
- [7. 📊 Monitoring Replication](#7--monitoring-replication)
- [8. 🛡️ Security Best Practices](#8-️-security-best-practices)
- [9. ⚠️ Important Limitations](#9-️-important-limitations)
- [10. 🧰 Troubleshooting](#10--troubleshooting)
- [11. ⚡ Quick Reference](#11--quick-reference)

---

## 1. 🎯 What Is Database Replication?

**Database replication** means maintaining a copy of a database on another PostgreSQL instance or server and transferring changes from the primary database to the replica.

For example, suppose your application uses a database called `company_db`.

Initially, it contains:

| id | name | salary |
|---:|---|---:|
| 1 | Rahul | 30000 |
| 2 | Priya | 40000 |

You insert a new record into the primary:

```sql
INSERT INTO public.employees (id, name, salary)
VALUES (3, 'Amit', 50000);
```

The replica receives the change automatically.

| id | name | salary |
|---:|---|---:|
| 1 | Rahul | 30000 |
| 2 | Priya | 40000 |
| 3 | Amit | 50000 |

The same principle applies to updates and deletes.

### 🔄 How Replication Works

```text
             🟢 PRIMARY DATABASE
                     |
              INSERT / UPDATE
                     |
                     v
          📝 Change records are generated
                     |
                     v
             🔄 Replication process
                     |
                     v
              🔵 REPLICA DATABASE
                     |
                     v
             📊 Updated data copy
```

### 💡 Why Use Replication?

- ⚡ Improve read performance.
- 📊 Run reporting and analytics queries on a separate instance.
- 🛡️ Maintain a standby for disaster recovery.
- 🔄 Keep a separate database synchronized.
- 📈 Scale applications that have many read requests.
- 🔧 Reduce the workload on the primary server.

**Important:** Replication is not a substitute for backups. Accidental deletions and corrupted data may also propagate to the replica.

---

## 2. 🧠 PostgreSQL Replication Types

PostgreSQL supports different replication approaches.

| Feature | 🔄 Physical Streaming Replication | 🧩 Logical Replication |
|---|---|---|
| Replication level | PostgreSQL cluster | Selected databases and tables |
| Data transfer | Write-ahead log (WAL) records | Logical changes to rows |
| Initial setup | Base backup | Initial table synchronization or prepared data |
| Replicates inserts, updates, and deletes | Yes | Yes, for supported published operations |
| Replicates schema changes | Physical copy includes database structures | Generally no |
| Standby normally read-only | Yes | Subscriber tables can be writable |
| Select specific tables | No | Yes |
| Typical use | High availability and standby servers | Selective synchronization and data integration |

### 🎯 Which One Should You Choose?

Choose **physical streaming replication** when you want a standby server containing a copy of the primary PostgreSQL cluster.

Choose **logical replication** when you want selected tables synchronized into a separate PostgreSQL database.

For a same-server logical replica, the publisher and subscriber must be separate PostgreSQL databases. For physical replication, they must be separate PostgreSQL clusters with their own data directories.

---

# 3. 🖥️ Replication on the Same Server

You can run two separate PostgreSQL instances on the same physical or virtual server.

For example:

```text
🖥️ ONE SERVER
│
├── 🟢 PostgreSQL Primary
│   ├── Port: 5432
│   └── Database: company_db
│
└── 🔵 PostgreSQL Replica
    ├── Port: 5433
    └── Database: company_db_replica
```

The primary and replica are separate PostgreSQL instances, not merely two databases in the same instance.

### 📌 When Is This Useful?

- 🧪 Development and testing.
- 📚 Learning PostgreSQL replication.
- 🧩 Testing logical replication.
- 🔬 Testing database migration procedures.
- 🛠️ Simulating a multi-instance architecture locally.

### ⚠️ Limitation

If the server crashes, loses its disk, or becomes unavailable, **both instances may become unavailable**.

Same-server replication can help isolate workloads, but it does not provide meaningful protection against a physical server failure.

---

## 3.1 🧩 Same-Server Logical Replication

Logical replication is often the easiest way to synchronize selected tables between two separate databases on one server.

### 🏗️ Architecture

```text
🖥️ Same Server
│
├── 🟢 PostgreSQL Instance
│   └── company_db
│       └── public.employees
│               |
│               | Logical replication
│               v
└── 🔵 PostgreSQL Instance
    └── company_db_replica
        └── public.employees
```

The example below assumes that the publisher and subscriber databases are hosted by separate PostgreSQL instances.

If they are hosted by the same instance, the logical replication setup is similar, but you must account for the instance's shared configuration and resource limits.

### Step 1️⃣: Configure the Publisher

Edit the primary instance's `postgresql.conf`:

```ini
wal_level = logical
max_replication_slots = 10
max_wal_senders = 10
```

These are example values. Choose limits based on your workload and the number of replication connections.

Restart PostgreSQL if required by the changed settings.

Check the configuration:

```sql
SHOW wal_level;
SHOW max_replication_slots;
SHOW max_wal_senders;
```

Expected:

```text
wal_level = logical
```

### Step 2️⃣: Create the Replication User

Connect to `company_db` on the publisher:

```sql
CREATE ROLE replication_user
WITH LOGIN REPLICATION PASSWORD 'replace_with_a_strong_password';
```

Grant the required access:

```sql
GRANT CONNECT ON DATABASE company_db
TO replication_user;

GRANT USAGE ON SCHEMA public
TO replication_user;

GRANT SELECT ON TABLE public.employees
TO replication_user;
```

The replication role must have the permissions required for replication and initial table synchronization.

For a production environment, grant access only to the required objects.

### Step 3️⃣: Create a Publication

On the publisher:

```sql
CREATE PUBLICATION company_publication
FOR TABLE public.employees;
```

A publication defines which table changes are available for logical replication.

To publish all eligible tables:

```sql
CREATE PUBLICATION company_publication
FOR ALL TABLES;
```

An all-tables publication has additional ownership requirements and does not automatically replicate schema changes.

### Step 4️⃣: Prepare the Subscriber Database

Create a separate database on the subscriber instance:

```sql
CREATE DATABASE company_db_replica;
```

Connect to the subscriber database and create a compatible table:

```sql
CREATE TABLE public.employees (
    id BIGINT PRIMARY KEY,
    name TEXT,
    salary NUMERIC(12, 2)
);
```

In a production environment, make sure the source and target schemas are compatible.

Logical replication does not automatically create target tables. PostgreSQL can perform initial table synchronization through a subscription, provided the required permissions and compatible tables are in place.

### Step 5️⃣: Create the Subscription

Run this on `company_db_replica`:

```sql
CREATE SUBSCRIPTION company_subscription
CONNECTION 'host=127.0.0.1 port=5432 dbname=company_db user=replication_user password=replace_with_a_strong_password'
PUBLICATION company_publication;
```

Replace the port and connection details with the actual publisher configuration.

The subscriber connects to the publisher and begins replicating published changes.

🔐 **Security:** Avoid placing real database passwords in source code, Git repositories, or shared documentation. Use a suitable secrets-management approach.

### Step 6️⃣: Test Replication

Insert a record on the publisher:

```sql
INSERT INTO public.employees (id, name, salary)
VALUES (1, 'Rahul', 30000);
```

Read the record from the subscriber:

```sql
SELECT *
FROM public.employees;
```

After replication processes the change, the row should appear.

Test an update:

```sql
UPDATE public.employees
SET salary = 35000
WHERE id = 1;
```

Test a delete:

```sql
DELETE FROM public.employees
WHERE id = 1;
```

The corresponding changes should be reflected on the subscriber.

---

## 3.2 🔄 Same-Server Physical Replication

Physical replication is also possible on the same machine, but it requires **two independent PostgreSQL clusters**, each with its own data directory and port.

Example:

```text
🖥️ Same Machine
│
├── 🟢 Primary Cluster
│   ├── Port: 5432
│   └── Data directory: /var/lib/postgresql/primary
│
└── 🔵 Standby Cluster
    ├── Port: 5433
    └── Data directory: /var/lib/postgresql/standby
```

The standby cluster must be initialized from a compatible base backup of the primary.

### General Setup

1. Configure the primary for physical replication.
2. Create a dedicated replication user.
3. Configure `pg_hba.conf` to allow the standby connection.
4. Take a base backup using `pg_basebackup`.
5. Configure the standby's connection and recovery settings.
6. Start the standby and verify replication.

Example primary configuration:

```ini
wal_level = replica
max_wal_senders = 10
max_replication_slots = 10
```

Create a replication user:

```sql
CREATE ROLE physical_replica
WITH LOGIN REPLICATION PASSWORD 'replace_with_a_strong_password';
```

A suitable `pg_hba.conf` entry for a local standby might be:

```text
host replication physical_replica 127.0.0.1/32 scram-sha-256
```

Reload the primary's configuration after changing `pg_hba.conf`.

A simplified base-backup command, run with appropriate operating-system permissions, might look like:

```bash
pg_basebackup \
  -h 127.0.0.1 \
  -p 5432 \
  -U physical_replica \
  -D /var/lib/postgresql/standby \
  -Fp \
  -Xs \
  -P \
  -R
```

**Important:** This is an illustrative command, not a complete universal installation procedure. The data directory must be empty, the PostgreSQL versions and environment must be compatible, and the standby must have the correct configuration, ownership, permissions, and port. Use the appropriate paths for your operating system and PostgreSQL installation.

`-R` creates standby configuration information, including connection settings and a standby signal file on supported PostgreSQL versions.

Start the standby using the service or command appropriate to that cluster.

Verify its state:

```sql
SELECT pg_is_in_recovery();
```

Expected on the standby:

```text
true
```

This setup is more involved than logical replication and is mainly useful for testing or specialized local workloads.

---

# 4. 🌐 Replication on Different Servers

This is a more useful architecture when you want a replica that remains available if the primary server fails.

Example:

```text
🌍 NETWORK
│
├── 🟢 Primary Server
│   ├── IP: 192.168.1.10
│   └── PostgreSQL Port: 5432
│
│          Replication Connection
│                   |
│                   v
│
└── 🔵 Replica Server
    ├── IP: 192.168.1.20
    └── PostgreSQL Port: 5432
```

The servers have separate storage and operating-system environments.

### 🎯 Benefits

- 🛡️ Better resilience against a single-server failure.
- ⚡ Read scaling.
- 🔄 A separate standby for disaster recovery.
- 📊 Independent compute resources for read workloads.
- 🧰 More flexibility for maintenance and migration.

### ⚠️ Important

Two servers alone do not guarantee automatic failover. Failover requires additional orchestration, health checks, and a strategy to prevent split-brain situations.

---

## 4.1 🧩 Different-Server Logical Replication

Logical replication is suitable when you want to synchronize selected tables between separate PostgreSQL databases.

### 🏗️ Architecture

```text
🖥️ Server A — Primary
│
└── PostgreSQL
    └── company_db
        └── public.employees
                |
                | Logical replication
                | TCP/IP
                v
🖥️ Server B — Subscriber
│
└── PostgreSQL
    └── company_db_replica
        └── public.employees
```

### Step 1️⃣: Configure the Publisher

On Server A, update `postgresql.conf`:

```ini
wal_level = logical
max_wal_senders = 10
max_replication_slots = 10
```

Restart PostgreSQL if required by the configuration change.

### Step 2️⃣: Allow the Subscriber to Connect

In the publisher's `pg_hba.conf`, add a restricted entry for the subscriber's IP address:

```text
host company_db replication_user 192.168.1.20/32 scram-sha-256
```

The entry above illustrates database-level access for the replication user. Ensure that the role has the required replication attributes and that the exact `pg_hba.conf` rule matches the connection type and PostgreSQL version.

Reload PostgreSQL after editing the file.

Do not expose PostgreSQL directly to the public internet without appropriate network and security controls.

### Step 3️⃣: Create the Replication User

On Server A:

```sql
CREATE ROLE replication_user
WITH LOGIN REPLICATION PASSWORD 'replace_with_a_strong_password';

GRANT CONNECT ON DATABASE company_db
TO replication_user;

GRANT USAGE ON SCHEMA public
TO replication_user;

GRANT SELECT ON TABLE public.employees
TO replication_user;
```

Grant only the required privileges.

### Step 4️⃣: Create a Publication

On Server A:

```sql
CREATE PUBLICATION company_publication
FOR TABLE public.employees;
```

### Step 5️⃣: Create the Target Database and Table

On Server B:

```sql
CREATE DATABASE company_db_replica;
```

Connect to `company_db_replica` and create a compatible table:

```sql
CREATE TABLE public.employees (
    id BIGINT PRIMARY KEY,
    name TEXT,
    salary NUMERIC(12, 2)
);
```

For existing data, arrange an initial copy or allow the subscription to perform initial table synchronization.

### Step 6️⃣: Create the Subscription

On Server B, connect to `company_db_replica`:

```sql
CREATE SUBSCRIPTION company_subscription
CONNECTION 'host=192.168.1.10 port=5432 dbname=company_db user=replication_user password=replace_with_a_strong_password'
PUBLICATION company_publication;
```

This creates a logical replication subscription to the primary.

Use a secure connection and appropriate secret handling in production.

### Step 7️⃣: Verify the Result

On Server A:

```sql
INSERT INTO public.employees (id, name, salary)
VALUES (1, 'Priya', 40000);
```

On Server B:

```sql
SELECT *
FROM public.employees;
```

The row should appear after replication processes it.

### 🔍 Check Subscription Status

On Server B:

```sql
SELECT
    subname,
    pid,
    received_lsn,
    latest_end_lsn,
    latest_end_time
FROM pg_stat_subscription;
```

A running subscription and current replication statistics help establish whether the subscription is active. Interpret the results in the context of your PostgreSQL version and workload.

---

## 4.2 🔄 Different-Server Physical Streaming Replication

For a complete standby of the primary PostgreSQL cluster, physical replication is often the preferred approach.

### 🏗️ Architecture

```text
🖥️ SERVER A — PRIMARY
│
├── PostgreSQL cluster
├── Port: 5432
├── Read/write
└── WAL generation
         |
         | Streaming WAL replication
         v
🖥️ SERVER B — STANDBY
│
├── Separate PostgreSQL cluster
├── Port: 5432
├── Normally read-only
└── Receives and replays WAL
```

### Step 1️⃣: Configure the Primary

In `postgresql.conf`:

```ini
wal_level = replica
max_wal_senders = 10
max_replication_slots = 10
```

Configure additional settings as needed for your retention, availability, and recovery requirements.

### Step 2️⃣: Create a Replication User

On Server A:

```sql
CREATE ROLE physical_replica
WITH LOGIN REPLICATION PASSWORD 'replace_with_a_strong_password';
```

### Step 3️⃣: Allow the Standby Server

Add an appropriate entry to the primary's `pg_hba.conf`:

```text
host replication physical_replica 192.168.1.20/32 scram-sha-256
```

Allow traffic through the firewall only from the intended standby or trusted network.

### Step 4️⃣: Take a Base Backup

On Server B, run `pg_basebackup` with the correct destination data directory:

```bash
pg_basebackup \
  -h 192.168.1.10 \
  -p 5432 \
  -U physical_replica \
  -D /var/lib/postgresql/standby \
  -Fp \
  -Xs \
  -P \
  -R
```

This command assumes a compatible PostgreSQL installation and an empty destination directory.

The PostgreSQL service must have appropriate ownership and permissions for the data directory.

### Step 5️⃣: Start the Standby

Start the standby cluster using the service manager or PostgreSQL commands appropriate to your environment.

Confirm that the standby is in recovery mode:

```sql
SELECT pg_is_in_recovery();
```

Expected:

```text
true
```

### Step 6️⃣: Verify the Primary Connection

On Server A:

```sql
SELECT
    application_name,
    client_addr,
    state,
    sync_state,
    sent_lsn,
    write_lsn,
    flush_lsn,
    replay_lsn
FROM pg_stat_replication;
```

You should see the connected standby when it is connected and replication is operating.

---

# 5. 🔄 Physical vs Logical Replication

The two approaches solve different problems.

### 🔄 Physical Replication

```text
Primary PostgreSQL Cluster
           |
           | WAL
           v
Standby PostgreSQL Cluster
```

- Replicates at the cluster level.
- Commonly used for standby servers and high availability.
- Normally provides a read-only standby.
- Requires compatible PostgreSQL cluster environments.
- Is not designed to replicate only selected tables.

### 🧩 Logical Replication

```text
Primary Database
    |
    ├── employees
    ├── departments
    └── payroll
          |
          | Publication
          v
Subscriber Database
    |
    └── Selected published tables
```

- Replicates selected tables and supported changes.
- Supports separate publisher and subscriber databases.
- Can support migrations and data integration.
- Requires compatible table structures and additional schema management.
- Does not automatically synchronize every database object.

### 📊 Comparison

| Requirement | Physical | Logical |
|---|---|---|
| Standby for high availability | ✅ Well suited | ⚠️ Different design |
| Selected tables only | ❌ | ✅ |
| Entire cluster copy | ✅ | ❌ |
| Separate target database | Possible as part of a separate cluster | ✅ |
| Independent writes on target | ❌ While in standby | Possible, but conflicts and divergence must be managed |
| Schema changes automatically synchronized | Physical structures are included | ❌ Generally not |

---

# 6. 👁️ Reading Data from a Replica

One major benefit of replication is separating read traffic from write traffic.

```text
              👤 Application
                    |
           ┌────────┴────────┐
           |                 |
           v                 v
     🟢 Primary          🔵 Replica
       Read/Write          Read
           |                 ^
           |                 |
           └── Replication ──┘
```

### 📝 Write Queries

Send write operations to the primary:

```sql
INSERT INTO public.employees (id, name, salary)
VALUES (2, 'Amit', 50000);
```

### 👁️ Read Queries

Send eligible read queries to the replica:

```sql
SELECT *
FROM public.employees
ORDER BY id;
```

### ⚠️ Replication Lag

Because replication can be asynchronous, a read immediately after a write might not return the newest data when executed on the replica.

If your application requires read-after-write consistency, read that data from the primary or implement a suitable consistency strategy.

### 🔐 Enforce Read-Only Access

For a physical standby, PostgreSQL normally prevents writes while it is in recovery.

For a logical subscriber, use appropriately restricted roles and permissions if the target is intended to be read-only.

Do not rely solely on application conventions to enforce read-only access.

---

# 7. 📊 Monitoring Replication

Monitoring helps identify replication failures, delays, and resource problems.

## 7.1 🔍 Monitor Physical Replication

On the primary:

```sql
SELECT
    application_name,
    client_addr,
    state,
    sync_state,
    sent_lsn,
    write_lsn,
    flush_lsn,
    replay_lsn
FROM pg_stat_replication;
```

This shows connected physical replication clients and their progress.

## 7.2 🔍 Check Whether the Server Is a Standby

Run on the server you want to inspect:

```sql
SELECT pg_is_in_recovery();
```

| Result | Meaning |
|---|---|
| `true` | The instance is in recovery, typically acting as a standby. |
| `false` | The instance is not currently in recovery. |

## 7.3 🧩 Monitor Logical Replication

On the publisher:

```sql
SELECT *
FROM pg_stat_replication;
```

On the subscriber:

```sql
SELECT *
FROM pg_stat_subscription;
```

These views expose useful replication state and progress information. The exact columns differ across PostgreSQL versions.

## 7.4 ⏱️ Check Physical Replication Lag

On the primary:

```sql
SELECT
    application_name,
    state,
    sync_state,
    write_lag,
    flush_lag,
    replay_lag
FROM pg_stat_replication;
```

Lag fields can be `NULL`, especially when the connection is idle or no recent measurements are available. They are not a universal measurement of the current amount of data waiting to be replicated.

## 7.5 📋 Check Replication Slots

Replication slots can retain WAL required by replicas or logical consumers.

On the publisher:

```sql
SELECT
    slot_name,
    slot_type,
    active,
    restart_lsn
FROM pg_replication_slots;
```

⚠️ An inactive slot can cause WAL to accumulate and consume disk space. Monitor slot health and WAL retention carefully.

---

# 8. 🛡️ Security Best Practices

### 🔐 1. Use Dedicated Replication Users

Create separate accounts for physical and logical replication where appropriate.

Avoid using a PostgreSQL superuser for routine replication connections.

### 🌐 2. Restrict Network Access

- Allow connections only from trusted hosts.
- Use firewall rules and private networking where possible.
- Avoid exposing PostgreSQL ports directly to the public internet.
- Use TLS for connections across networks.

### 🔑 3. Protect Credentials

- Store passwords in a secrets manager or secure configuration.
- Do not commit connection strings containing passwords to Git.
- Rotate credentials when required.
- Restrict access to configuration files.

### 📂 4. Restrict Database Permissions

Grant access only to the tables and schemas required by the replication user.

### 📊 5. Monitor WAL and Replication Slots

Physical and logical replication can retain WAL files when a replica is disconnected or falls behind.

Monitor disk space, replication slots, and replication lag.

### 🛡️ 6. Test Failover and Recovery

A replica is useful only if you know how to recover from a failure.

Test:
- Standby promotion.
- Application connection changes.
- Recovery from a failed primary.
- Backup restoration.
- Replication reconnection and resynchronization.

### 💾 7. Keep Independent Backups

Replication copies changes; backups provide recovery points.

Maintain automated backups and, where appropriate, point-in-time recovery.

---

# 9. ⚠️ Important Limitations

### ❗ 1. Replication Is Not Always Instant

Asynchronous replication introduces some delay.

### ❗ 2. Deletes Are Replicated Too

Deleting a record on the primary can delete the corresponding record on the replica.

### ❗ 3. Schema Changes Need Special Attention

Logical replication does not automatically propagate every DDL change.

Coordinate schema migrations across the publisher and subscriber.

### ❗ 4. Replication Is Not a Backup

A replica may reproduce accidental deletions or unwanted updates.

### ❗ 5. Replicas Consume Resources

A replica requires CPU, memory, storage, network bandwidth, and monitoring.

Two PostgreSQL instances on the same server share the machine's hardware resources.

### ❗ 6. Logical Replication Has Limitations

Logical replication does not automatically synchronize all database objects, sequences, and every kind of database change.

### ❗ 7. Physical Standbys Are Normally Read-Only

A physical standby cannot normally accept ordinary application writes while operating in recovery.

### ❗ 8. Automatic Failover Requires Additional Components

Streaming replication alone does not automatically guarantee safe failover or prevent split-brain situations.

---

# 10. 🧰 Troubleshooting

| Problem | Possible Cause | What to Check |
|---|---|---|
| Replica cannot connect | Firewall, routing, or authentication issue | Network access, `pg_hba.conf`, credentials |
| Logical subscription fails | Incorrect publication or privileges | Publication, subscription, role permissions |
| Initial synchronization fails | Incompatible target table or missing permissions | Table definitions and replication logs |
| Changes are delayed | Network or subscriber workload | Replication statistics and server logs |
| WAL disk usage increases | Replica is disconnected or slot retains WAL | Replication slots and WAL retention |
| Standby does not start | Incorrect data directory or recovery configuration | PostgreSQL logs and file permissions |
| Query fails on replica | Replica is in recovery or role lacks access | Role permissions and recovery status |
| Schema changes are missing | Logical replication does not synchronize DDL automatically | Apply compatible schema changes on the subscriber |
| Duplicate-key conflict on subscriber | Independent writes or data divergence | Subscriber write activity and replication logs |

### 🔍 Useful Diagnostic Commands

Check the PostgreSQL version:

```sql
SELECT version();
```

Check the configured port:

```sql
SHOW port;
```

Check WAL level:

```sql
SHOW wal_level;
```

Check active replication connections:

```sql
SELECT *
FROM pg_stat_replication;
```

Check replication slots:

```sql
SELECT *
FROM pg_replication_slots;
```

For operating-system-level problems, also inspect the PostgreSQL service status and logs.

---

# 11. ⚡ Quick Reference

| Task | Command or Setting |
|---|---|
| 🔍 Check WAL level | `SHOW wal_level;` |
| 🔍 Check recovery state | `SELECT pg_is_in_recovery();` |
| 📊 Monitor replication | `SELECT * FROM pg_stat_replication;` |
| 🔍 Check replication slots | `SELECT * FROM pg_replication_slots;` |
| 🧩 Monitor logical subscription | `SELECT * FROM pg_stat_subscription;` |
| 📝 Create a publication | `CREATE PUBLICATION company_publication FOR TABLE public.employees;` |
| 🔗 Create a subscription | `CREATE SUBSCRIPTION company_subscription CONNECTION '...' PUBLICATION company_publication;` |
| 🔑 Create a replication role | `CREATE ROLE physical_replica WITH LOGIN REPLICATION PASSWORD 'strong_password';` |
| 🛠️ Configure logical replication | `wal_level = logical` |
| 🛠️ Configure physical replication | `wal_level = replica` |
| 💾 Create a physical standby | Use `pg_basebackup` with the correct data directory and connection settings |

---

# 🎯 Final Recommendation

Choose your architecture according to the problem you want to solve.

| Your Goal | Recommended Approach |
|---|---|
| 🧪 Learn replication locally | Logical replication between separate local databases |
| 🖥️ Test multiple PostgreSQL instances on one machine | Separate instances with separate ports and data directories |
| 📊 Run analytics without overloading the primary | Read replica |
| 🛡️ Prepare for server failure | Physical streaming replication on a different server |
| 🧩 Replicate selected tables | Logical replication |
| 💾 Recover accidentally deleted data | Backups and point-in-time recovery |
| 🔄 Synchronize databases across servers | Logical or physical replication, depending on the requirements |

## 🧠 Remember

- **Same server:** Useful for development, testing, and workload isolation, but it does not protect against server failure.
- **Different servers:** Better for high availability and resilience, provided failover and recovery are properly designed.
- **Physical replication:** Best suited to a standby copy of a PostgreSQL cluster.
- **Logical replication:** Best suited to synchronizing selected tables between databases.
- **Backups:** Essential even when replication is configured.

**Best starting point:** Learn logical replication between two separate local PostgreSQL instances first. Then explore physical streaming replication between two servers for high availability.
