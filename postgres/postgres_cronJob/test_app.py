from __future__ import annotations

import pytest

from app import validate_database_url


def test_validate_database_url_accepts_postgresql_dsn() -> None:
    validate_database_url(
        "postgresql://cron_lab:local-only-change-me@127.0.0.1:5434/cron_lab"
    )


@pytest.mark.parametrize(
    "database_url",
    [
        "127.0.0.1:5434/cron_lab",
        "mysql://cron_lab:password@127.0.0.1:5434/cron_lab",
        "postgresql://127.0.0.1:5434/",
        "",
    ],
)
def test_validate_database_url_rejects_malformed_dsn(database_url: str) -> None:
    with pytest.raises(RuntimeError, match="DATABASE_URL must be a PostgreSQL URL"):
        validate_database_url(database_url)
