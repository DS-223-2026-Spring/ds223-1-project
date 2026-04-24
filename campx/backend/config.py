"""Configuration helpers for the backend service."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


PROJECT_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_DIR / ".env"


def load_backend_env() -> Path:
    """Load the project-level environment file for local scripts."""
    load_dotenv(ENV_FILE, override=False)
    return ENV_FILE


def running_in_container() -> bool:
    return Path("/.dockerenv").exists()


def _normalize_db_host(raw_host: str | None) -> str:
    if raw_host and raw_host != "db":
        return raw_host
    if running_in_container():
        return "db"
    return "localhost"


def _normalize_db_port(raw_port: str | int | None, *, raw_host: str | None) -> int:
    if raw_port is None:
        return 5432 if running_in_container() else 5434

    port = int(raw_port)
    if not running_in_container() and raw_host == "db" and port == 5432:
        # docker-compose publishes postgres on 5434 for host-side scripts.
        return 5434
    return port


@lru_cache(maxsize=1)
def get_database_settings() -> dict[str, object]:
    """Read database settings with local-friendly defaults."""
    load_backend_env()

    raw_host = os.getenv("DB_HOST") or os.getenv("POSTGRES_HOST")
    raw_port = os.getenv("DB_PORT") or os.getenv("POSTGRES_PORT")

    return {
        "host": _normalize_db_host(raw_host),
        "port": _normalize_db_port(raw_port, raw_host=raw_host),
        "dbname": os.getenv("POSTGRES_DB") or os.getenv("DB_NAME") or "campaign",
        "user": os.getenv("POSTGRES_USER") or os.getenv("DB_USER") or "campaign_user",
        "password": os.getenv("POSTGRES_PASSWORD") or os.getenv("DB_PASSWORD") or "campaign_pass",
    }
