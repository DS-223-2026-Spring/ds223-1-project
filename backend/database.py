"""Compatibility shim for backend database helpers."""

from app.config import get_database_settings, load_backend_env
from app.database import create_db_handler, get_db

