"""Multi-layer memory writer and storage adapters for LearnMate AI.

Consolidates persistence across:
1. SQLite (relational) — session summary, skill scores, memory fragments.
2. ChromaDB (semantic) — vector embeddings for RAG retrieval.
3. LangGraph Store (LTM) — cross-thread key-value long-term memory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@dataclass
class MemoryFacts:
    """Structured facts extracted from session / graph state for long-term storage."""

    session_id: int | None = None
    topic: str = "General"
    diagnosis: str = ""
    style: str = "unknown"
    summary: str = ""
    skill_scores: dict[str, float] = field(default_factory=dict)
    topics_learned: list[str] = field(default_factory=list)
    topics_need_practice: list[str] = field(default_factory=list)

    @classmethod
    def from_state(cls, state: dict[str, Any]) -> MemoryFacts:
        """Construct MemoryFacts from a LangGraph ALCState mapping."""
        return cls(
            session_id=state.get("session_id"),
            topic=state.get("current_topic", "General"),
            diagnosis=state.get("latest_diagnosis", ""),
            style=state.get("detected_learning_style", "unknown"),
            summary=state.get("session_summary", ""),
            skill_scores=dict(state.get("skill_scores") or {}),
            topics_learned=list(state.get("topics_learned") or []),
            topics_need_practice=list(state.get("topics_need_practice") or []),
        )

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)


@runtime_checkable
class MemoryAdapter(Protocol):
    """Protocol for memory persistence adapters."""

    def write(self, student_id: int, facts: MemoryFacts) -> None:
        """Write facts for the given student to the underlying store."""
        ...


class SqliteAdapter:
    """Relational adapter persisting session summaries, skill scores, and memory fragments."""

    def __init__(self, db_session) -> None:
        self.db_session = db_session

    def write(self, student_id: int, facts: MemoryFacts) -> None:
        if self.db_session is None:
            return

        from backend.app.models.memory import Memory
        from backend.app.models.session import Session as SessionModel
        from backend.app.models.skill import Skill

        # 1. Update session summary & ended_at
        if facts.session_id:
            sess = self.db_session.get(SessionModel, facts.session_id)
            if sess:
                if facts.summary:
                    sess.summary = facts.summary
                sess.ended_at = datetime.now(timezone.utc)
                logger.info(
                    "💾 [MEMORY] Saved session summary for session_id=%s",
                    facts.session_id,
                )

        # 2. Update skill mastery scores
        for skill_name, score in (facts.skill_scores or {}).items():
            skill = (
                self.db_session.query(Skill)
                .filter_by(student_id=student_id, skill_name=skill_name)
                .first()
            )
            if skill:
                skill.mastery_score = max(0.0, min(100.0, float(score)))
                skill.updated_at = datetime.now(timezone.utc)
        if facts.skill_scores:
            logger.info(
                "💾 [MEMORY] Updated skill scores for student %s: %s",
                student_id,
                facts.skill_scores,
            )

        # 3. Store memory fragments
        if facts.topics_need_practice:
            self.db_session.add(
                Memory(
                    student_id=student_id,
                    memory_type="weakness",
                    content=f"Needs practice: {', '.join(facts.topics_need_practice)}",
                )
            )
        if facts.topics_learned:
            self.db_session.add(
                Memory(
                    student_id=student_id,
                    memory_type="strength",
                    content=f"Learned: {', '.join(facts.topics_learned)}",
                )
            )
        if facts.style != "unknown":
            self.db_session.add(
                Memory(
                    student_id=student_id,
                    memory_type="preference",
                    content=f"Preferred learning style: {facts.style}",
                )
            )
        if facts.diagnosis:
            self.db_session.add(
                Memory(
                    student_id=student_id,
                    memory_type="context",
                    content=f"Diagnosis: {facts.diagnosis[:500]}",
                )
            )
        logger.info(
            "💾 [MEMORY] Stored memory fragments for student %s",
            student_id,
        )


class ChromaAdapter:
    """Semantic adapter embedding memory fragments in ChromaDB for RAG retrieval."""

    def __init__(self, embed_fn=None) -> None:
        self.embed_fn = embed_fn

    def write(self, student_id: int, facts: MemoryFacts) -> None:
        embed = self.embed_fn
        if embed is None:
            try:
                from backend.app.services.chroma_service import embed_memory
                embed = embed_memory
            except Exception:
                logger.debug("💾 [MEMORY] ChromaDB service unavailable.")
                return

        fragments = []
        if facts.topics_need_practice:
            fragments.append(("weakness", f"Needs practice: {', '.join(facts.topics_need_practice)}"))
        if facts.topics_learned:
            fragments.append(("strength", f"Learned: {', '.join(facts.topics_learned)}"))
        if facts.style != "unknown":
            fragments.append(("preference", f"Preferred learning style: {facts.style}"))
        if facts.diagnosis:
            fragments.append(("context", f"Diagnosis: {facts.diagnosis[:500]}"))

        for mtype, content in fragments:
            try:
                embed(student_id=student_id, memory_type=mtype, content=content)
            except Exception:
                logger.debug("💾 [MEMORY] ChromaDB embed skipped for %s", mtype)


class StoreAdapter:
    """Cross-thread long-term memory adapter writing to LangGraph Store."""

    def __init__(self, store=None) -> None:
        self.store = store

    def write(self, student_id: int, facts: MemoryFacts) -> None:
        store = self.store
        if store is None:
            try:
                from langgraph.config import get_store
                store = get_store()
            except Exception:
                store = None

        if store is None:
            return

        try:
            ns = (f"student_{student_id}", "memories")
            now_iso = datetime.now(timezone.utc).isoformat()

            if facts.style != "unknown":
                store.put(
                    ns,
                    "learning_style",
                    {"style": facts.style, "topic": facts.topic, "updated_at": now_iso},
                )
            if facts.topics_need_practice:
                store.put(
                    ns,
                    "weaknesses",
                    {"topics": facts.topics_need_practice, "updated_at": now_iso},
                )
            if facts.topics_learned:
                store.put(
                    ns,
                    "strengths",
                    {"topics": facts.topics_learned, "updated_at": now_iso},
                )
            if facts.diagnosis:
                store.put(
                    ns,
                    "context",
                    {"diagnosis": facts.diagnosis[:500], "topic": facts.topic, "updated_at": now_iso},
                )
            if facts.summary and facts.session_id:
                store.put(
                    ns,
                    f"session_summary_{facts.session_id}",
                    {"summary": facts.summary, "topic": facts.topic, "updated_at": now_iso},
                )

            logger.info(
                "💾 [LTM] Wrote cross-thread memories to Store for student %s",
                student_id,
            )
        except Exception:
            logger.debug(
                "💾 [LTM] Store write skipped for student %s",
                student_id,
                exc_info=True,
            )


class MemoryWriter:
    """Orchestrates multi-layer memory persistence and transaction lifecycle.

    Consolidates writes to SQLite, ChromaDB, and LangGraph Store.
    Manages commit and rollback internally so callers never need to touch db_session.commit().
    """

    def __init__(
        self,
        db_session=None,
        sqlite_adapter: SqliteAdapter | None = None,
        chroma_adapter: ChromaAdapter | None = None,
        store_adapter: StoreAdapter | None = None,
    ) -> None:
        self.db_session = db_session
        if sqlite_adapter is not None:
            self.sqlite_adapter = sqlite_adapter
            if self.db_session is None and hasattr(sqlite_adapter, "db_session"):
                self.db_session = sqlite_adapter.db_session
        elif db_session is not None:
            self.sqlite_adapter = SqliteAdapter(db_session)
        else:
            self.sqlite_adapter = None

        self.chroma_adapter = chroma_adapter if chroma_adapter is not None else ChromaAdapter()
        self.store_adapter = store_adapter if store_adapter is not None else StoreAdapter()

    def persist(self, student_id: int, facts: MemoryFacts | dict[str, Any]) -> None:
        """Persist memory facts across all configured storage adapters.

        Manages SQLite transaction (commit on success, rollback on error).
        Chroma and Store adapters are called and failures are caught gracefully.
        """
        if isinstance(facts, dict):
            facts = MemoryFacts.from_state(facts)

        # 1. Relational persistence (SQLite) with internal commit / rollback
        if self.sqlite_adapter is not None:
            try:
                self.sqlite_adapter.write(student_id, facts)
                if self.db_session is not None:
                    self.db_session.commit()
            except Exception:
                logger.exception(
                    "💾 [MEMORY] Error saving session data for student %s",
                    student_id,
                )
                if self.db_session is not None:
                    try:
                        self.db_session.rollback()
                    except Exception:
                        pass

        # 2. Vector persistence (ChromaDB)
        if self.chroma_adapter is not None:
            try:
                self.chroma_adapter.write(student_id, facts)
            except Exception:
                logger.debug("💾 [MEMORY] ChromaAdapter write failed", exc_info=True)

        # 3. Cross-thread key-value persistence (LangGraph Store)
        if self.store_adapter is not None:
            try:
                self.store_adapter.write(student_id, facts)
            except Exception:
                logger.debug("💾 [LTM] StoreAdapter write failed", exc_info=True)
