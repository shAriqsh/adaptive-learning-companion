"""LangGraph memory primitives — checkpointer (STM) and store (LTM).

This module provides singleton access to:

- **SqliteSaver** (Short-Term Memory): Persists graph state per thread_id.
  Conversation history survives server restarts.
- **InMemoryStore** (Long-Term Memory): Cross-thread key-value store
  namespaced per student.  Complements ChromaDB semantic search and the
  SQLite ``memories`` table.

Both are lazily initialised on first access.
"""

from __future__ import annotations

import logging
import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.memory import InMemoryStore

from backend.app.config import settings

logger = logging.getLogger(__name__)

# ── Singletons ────────────────────────────────────────────────────────────

_checkpointer: SqliteSaver | None = None
_store: InMemoryStore | None = None


def get_checkpointer() -> SqliteSaver:
    """Return the module-level ``SqliteSaver`` singleton.

    The SQLite connection uses ``check_same_thread=False`` because
    FastAPI serves requests from a thread-pool, and ``SqliteSaver``
    has its own internal locking.
    """
    global _checkpointer  # noqa: PLW0603

    if _checkpointer is None:
        db_path = settings.CHECKPOINT_DB_PATH
        conn = sqlite3.connect(db_path, check_same_thread=False)
        _checkpointer = SqliteSaver(conn)
        logger.info(
            "🧠 [STM] SqliteSaver checkpointer initialised → %s", db_path
        )

    return _checkpointer


def get_memory_store() -> InMemoryStore:
    """Return the module-level ``InMemoryStore`` singleton.

    All cross-thread (long-term) memories live here, namespaced by
    ``("student_{id}", "memories")``.
    """
    global _store  # noqa: PLW0603

    if _store is None:
        _store = InMemoryStore()
        logger.info("🧠 [LTM] InMemoryStore initialised")

    return _store


# ── Test helpers ──────────────────────────────────────────────────────────

def create_test_checkpointer() -> SqliteSaver:
    """Create an **in-memory** checkpointer for test isolation.

    Each call returns a brand-new instance — tests don't share state.
    """
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    return SqliteSaver(conn)


def create_test_store() -> InMemoryStore:
    """Create a fresh ``InMemoryStore`` for test isolation."""
    return InMemoryStore()


def reset_singletons() -> None:
    """Reset module-level singletons (useful in tests).

    Closes the existing checkpointer connection if one is open.
    """
    global _checkpointer, _store  # noqa: PLW0603

    if _checkpointer is not None:
        try:
            _checkpointer.conn.close()
        except Exception:
            pass
    _checkpointer = None
    _store = None
