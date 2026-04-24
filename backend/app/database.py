"""Database connection helpers for the FastAPI backend."""

from __future__ import annotations

from collections.abc import Generator

from fastapi import HTTPException
from psycopg2 import OperationalError

from app.config import get_database_settings
from app.shared.SQLHandler import SQLHandler


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

