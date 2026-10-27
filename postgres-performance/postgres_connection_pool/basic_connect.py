from __future__ import annotations

import asyncio
import os

import asyncpg

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres_lab:local-only-change-me@127.0.0.1:5436/postgres_lab",
)


async def main() -> None:
    connection = await asyncpg.connect(DATABASE_URL)
    try:
        row = await connection.fetchrow(
            "SELECT current_database() AS database, version() AS server_version"
        )
        print(f"Database: {row['database']}")
        print(f"Server: {row['server_version']}")
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(main())
