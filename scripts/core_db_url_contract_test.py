#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

from app.db import clean_asyncpg_url, database_url  # noqa: E402


@contextmanager
def env(**values: str | None):
    previous = {key: os.environ.get(key) for key in values}
    try:
        for key, value in values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def main() -> int:
    source = "postgresql://user:pass@db.example:5432/resort?schema=public&sslmode=require&connect_timeout=7"
    cleaned = clean_asyncpg_url(source)
    assert "schema=" not in cleaned
    assert "sslmode=require" in cleaned
    assert "connect_timeout=7" in cleaned
    assert cleaned.startswith("postgresql://user:pass@db.example:5432/resort?")

    middle = clean_asyncpg_url("postgresql://user:pass@db.example/resort?sslmode=require&schema=public&application_name=resort")
    assert "schema=" not in middle
    assert "sslmode=require" in middle
    assert "application_name=resort" in middle

    with env(APP_ENV="production", DATABASE_URL=None):
        try:
            database_url()
        except RuntimeError as exc:
            assert "DATABASE_URL is required in production" in str(exc)
        else:
            raise AssertionError("production DATABASE_URL must fail closed")

    with env(APP_ENV="development", DATABASE_URL=None):
        value = database_url()
        assert value.startswith("postgresql://resort:resort@localhost:5432/resort_os")

    with env(APP_ENV="production", DATABASE_URL=source):
        value = database_url()
        assert value == cleaned

    print("PASS: Core production DATABASE_URL fails closed and preserves DBaaS transport parameters")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
