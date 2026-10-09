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


@pytest.fixture()
def memory_writer(db):
    """Yield a MemoryWriter configured with in-memory SQLite, mock ChromaDB, and InMemoryStore."""
    from unittest.mock import MagicMock
    from backend.app.memory.writer import MemoryWriter, ChromaAdapter, StoreAdapter
    from backend.app.agents.checkpointer import create_test_store

    mock_embed = MagicMock()
    chroma_adapter = ChromaAdapter(embed_fn=mock_embed)
    store = create_test_store()
    store_adapter = StoreAdapter(store=store)

    writer = MemoryWriter(
        db_session=db,
        chroma_adapter=chroma_adapter,
        store_adapter=store_adapter,
    )
    writer._test_store = store
    writer._mock_embed = mock_embed
    return writer


@pytest.fixture()
def memory_reader(db, memory_writer):
    """Yield a MemoryReader wired to the same test backends as memory_writer."""
    from backend.app.memory.reader import MemoryReader

    def _mock_retrieve_chroma(student_id: int, query: str, k: int = 5) -> list[str]:
        return [
            call.kwargs.get("content")
            for call in memory_writer._mock_embed.call_args_list
            if call.kwargs.get("student_id") == student_id and call.kwargs.get("content")
        ][:k]

    return MemoryReader(
        db_session=db,
        chroma_service=_mock_retrieve_chroma,
        store=memory_writer._test_store,
    )



@pytest.fixture()
def fake_llm():
    """Yield a deterministic FakeListChatModel returning canned responses."""
    from langchain_core.language_models.fake_chat_models import FakeListChatModel

    return FakeListChatModel(
        responses=[
            '{"correct": true, "explanation": "Spot on!"}',
            '{"question": "What is 2+2?", "correct_answer": "4", "hint": "Basic addition"}',
            '{"session_summary": "Great session.", "topics_learned": ["Addition"], "topics_need_practice": []}',
            "You are doing wonderfully! Let's continue.",
        ]
    )


@pytest.fixture()
def fake_llm_factory():
    """Factory fixture returning a function to create FakeListChatModel with custom responses."""
    from langchain_core.language_models.fake_chat_models import FakeListChatModel

    def _create(responses: list[str]) -> FakeListChatModel:
        return FakeListChatModel(responses=responses)

    return _create


