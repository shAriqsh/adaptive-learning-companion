"""Shared test fixtures for LearnMate AI tests."""
import os
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure the project root is on sys.path so `backend.app...` imports work.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Force a test-only in-memory SQLite database BEFORE any app modules are imported.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("GOOGLE_API_KEY", "test-key-not-real")

from backend.app.database import Base  # noqa: E402
import backend.app.models  # noqa: F401, E402



@pytest.fixture()
def db():
    """Yield a fresh, isolated SQLAlchemy session backed by in-memory SQLite.

    Tables are created before each test and torn down after.
    """
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def checkpointer():
    """Yield a fresh in-memory SqliteSaver for test isolation."""
    from backend.app.agents.checkpointer import create_test_checkpointer

    cp = create_test_checkpointer()
    yield cp
    try:
        cp.conn.close()
    except Exception:
        pass


@pytest.fixture()
def memory_store():
    """Yield a fresh InMemoryStore for test isolation."""
    from backend.app.agents.checkpointer import create_test_store

    return create_test_store()
