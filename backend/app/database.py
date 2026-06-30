from __future__ import annotations

from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.app.config import settings

# ── Engine & Session Factory ──────────────────────────────────────────────

engine = create_engine(
    settings.DATABASE_URL,
    # SQLite-specific: allow usage across threads (required for FastAPI)
    connect_args={"check_same_thread": False}
    if settings.DATABASE_URL.startswith("sqlite")
    else {},
    echo=settings.DEBUG,
)

SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# ── Declarative Base ──────────────────────────────────────────────────────

class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


# ── FastAPI Dependency ────────────────────────────────────────────────────

def get_db() -> Generator[Session, Any, None]:
    """Yield a database session and ensure it is closed after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Table Initialization ─────────────────────────────────────────────────

def init_db() -> None:
    """Create all tables that don't exist yet.

    Models must be imported before calling this so that ``Base.metadata``
    is fully populated.
    """
    # Ensure all model modules are imported (they register with Base)
    import backend.app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
