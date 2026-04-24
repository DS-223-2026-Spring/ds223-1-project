"""Compatibility entrypoint for the backend FastAPI app."""

from app.database import get_db
from app.main import app, build_description
