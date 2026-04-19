"""
SQLAlchemy ORM models — aligned with full simulation schema.
Owner: Victoria Makaryan (backend branch)
Validate against db/init.sql if adding columns.
"""
from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, ForeignKey, LargeBinary
from sqlalchemy.sql import func
from database import Base
