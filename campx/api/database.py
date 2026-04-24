"""Database connection helpers for the FastAPI backend."""

from __future__ import annotations

import os
from typing import Generator

from fastapi import HTTPException
from psycopg2 import OperationalError

from SQLHandler import SQLHandler


def get_database_settings() -> dict[str, object]:
    """Read database settings from the shared compose/.env configuration."""
    in_container = os.path.exists("/.dockerenv")

    return {
        "host": os.getenv("DB_HOST")
        or os.getenv("POSTGRES_HOST")
        or ("db" if in_container else "localhost"),
        "port": int(os.getenv("DB_PORT") or os.getenv("POSTGRES_PORT") or 5432),
        "dbname": os.getenv("POSTGRES_DB") or os.getenv("DB_NAME") or "campaign",
        "user": os.getenv("POSTGRES_USER") or os.getenv("DB_USER") or "campaign_user",
        "password": os.getenv("POSTGRES_PASSWORD")
        or os.getenv("DB_PASSWORD")
        or "campaign_pass",
    }


def create_db_handler() -> SQLHandler:
    """Create a fresh SQLHandler for a request."""
    return SQLHandler(**get_database_settings())


def get_db() -> Generator[SQLHandler, None, None]:
    """
    FastAPI dependency that opens and closes a DB session per request.

    DB-backed routes return a 503 until the shared postgres service is available.
    """
    db = None
    try:
        db = create_db_handler()
        yield db
    except OperationalError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Database dependency unavailable. Start the 'db' service before "
                "calling DB-backed backend endpoints."
            ),
        ) from exc
    finally:
        if db is not None:
            db.close()
