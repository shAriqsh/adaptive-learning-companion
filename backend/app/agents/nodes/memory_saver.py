"""Memory Saver node — persists session data across three layers.

This is a side-effect-only node that extracts memory facts from the graph state
and delegates persistence to ``MemoryWriter`` (SQLite, ChromaDB, and LangGraph Store).

Returns an empty dict so it doesn't alter the graph state.
"""

from __future__ import annotations

import logging

from backend.app.agents.state import ALCState
from backend.app.memory.writer import MemoryFacts, MemoryWriter

logger = logging.getLogger(__name__)


def make_memory_saver(db_session=None, memory_writer: MemoryWriter | None = None):
    """Create a ``node_memory_saver`` closure bound to a DB session or MemoryWriter.

    Using a closure lets us inject the database session or MemoryWriter at graph-build
    time without polluting the LangGraph state with ORM objects.

    Args:
        db_session: A SQLAlchemy ``Session`` instance, or ``None`` for
                    a no-op (useful in tests and early development).
        memory_writer: Optional pre-configured ``MemoryWriter`` instance.
                       If not provided, one is instantiated from ``db_session``.

    Returns:
        A node function ``(ALCState) -> dict``.
    """
    writer = memory_writer if memory_writer is not None else MemoryWriter(db_session=db_session)

    def node_memory_saver(state: ALCState) -> dict:
        """Persist session data via MemoryWriter (side-effect only).

        Returns an empty dict — this node does not modify graph state.
        """
        student_id = state.get("student_id", 0)
        facts = MemoryFacts.from_state(state)
        writer.persist(student_id, facts)
        return {}

    return node_memory_saver


# Convenience: a default saver for use when no DB is available.
node_memory_saver = make_memory_saver(db_session=None)
