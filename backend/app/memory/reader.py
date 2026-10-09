"""Memory retrieval reader for LearnMate AI.

Consolidates multi-layer memory retrieval across:
1. LangGraph Store (cross-thread structured memories)
2. ChromaDB (semantic similarity RAG)
3. SQLite (recent relational memory fragments)
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class MemoryReader:
    """Consolidated reader for multi-tier student long-term memory retrieval."""

    def __init__(
        self,
        db_session: Any = None,
        chroma_service: Any = None,
        store: Any = None,
    ) -> None:
        self.db_session = db_session
        self.chroma_service = chroma_service
        self.store = store

    def _retrieve_from_store(self, student_id: int) -> list[str]:
        """Fetch structured cross-thread memories from LangGraph Store."""
        store = self.store
        if store is None:
            try:
                from langgraph.config import get_store

                store = get_store()
            except Exception:
                store = None

        if store is None:
            return []

        memories: list[str] = []
        try:
            ns = (f"student_{student_id}", "memories")
            for key in ("learning_style", "weaknesses", "strengths", "context"):
                item = store.get(ns, key)
                if item and item.value:
                    val = item.value
                    if key == "learning_style":
                        style = val.get("style", "unknown")
                        if style and style != "unknown":
                            memories.append(f"Preferred learning style: {style}")
                    elif key == "weaknesses":
                        topics = val.get("topics", [])
                        if topics:
                            memories.append(f"Needs practice: {', '.join(topics)}")
                    elif key == "strengths":
                        topics = val.get("topics", [])
                        if topics:
                            memories.append(f"Learned: {', '.join(topics)}")
                    elif key == "context":
                        diag = val.get("diagnosis", "")
                        if diag:
                            memories.append(f"Prior diagnosis: {diag[:300]}")
        except Exception:
            logger.debug("🔍 [LTM] Store retrieval error for student %s", student_id, exc_info=True)

        return memories

    def _retrieve_from_chroma(self, student_id: int, query: str, k: int) -> list[str]:
        """Fetch semantic memories via ChromaDB vector search."""
        if not query:
            return []

        try:
            if self.chroma_service is not None:
                if callable(self.chroma_service):
                    return list(self.chroma_service(student_id, query, k) or [])
                if hasattr(self.chroma_service, "retrieve_memories"):
                    return list(self.chroma_service.retrieve_memories(student_id=student_id, query=query, k=k) or [])

            from backend.app.services.chroma_service import retrieve_memories

            return list(retrieve_memories(student_id=student_id, query=query, k=k) or [])
        except Exception:
            logger.debug("🔍 [RAG] ChromaDB retrieval error for student %s", student_id, exc_info=True)
            return []

    def _retrieve_from_sqlite(self, student_id: int, k: int) -> list[str]:
        """Fetch recent memory fragments from SQLite relational table."""
        if self.db_session is None:
            return []

        try:
            from backend.app.services.memory_service import get_memories

            mems = get_memories(self.db_session, student_id, limit=k)
            return [m.content for m in mems if m and getattr(m, "content", None)]
        except Exception:
            logger.debug("🔍 [RAG] SQLite retrieval error for student %s", student_id, exc_info=True)
            return []

    def retrieve(self, student_id: int, query: str = "", k: int = 5) -> list[str]:
        """Retrieve relevant memories for a student, merging Store, Chroma, and SQLite.

        Queries all three layers, merges and deduplicates results while preserving order.
        If a backend is unavailable or fails, gracefully proceeds with the others.

        Args:
            student_id: The student to retrieve memories for.
            query: Semantic query text (e.g. topic).
            k: Max number of memories to return (default 5).

        Returns:
            List of memory strings, ordered and deduplicated.
        """
        store_memories = self._retrieve_from_store(student_id)
        chroma_memories = self._retrieve_from_chroma(student_id, query, k)
        sqlite_memories = self._retrieve_from_sqlite(student_id, k)

        combined = store_memories + chroma_memories + sqlite_memories

        seen: set[str] = set()
        deduped: list[str] = []
        for mem in combined:
            if not isinstance(mem, str):
                continue
            cleaned = mem.strip()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                deduped.append(cleaned)

        if k is not None and k > 0:
            return deduped[:k]
        return deduped
