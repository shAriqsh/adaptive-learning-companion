"""Memory Saver node — persists session data to the database.

This is a side-effect-only node: it saves session summaries, updates
mastery scores, and stores memory fragments, but returns an empty dict
so it doesn't alter the graph state.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from backend.app.agents.state import ALCState

logger = logging.getLogger(__name__)


def make_memory_saver(db_session=None):
    """Create a ``node_memory_saver`` closure bound to a DB session.

    Using a closure lets us inject the database session at graph-build
    time without polluting the LangGraph state with ORM objects.

    Args:
        db_session: A SQLAlchemy ``Session`` instance, or ``None`` for
                    a no-op (useful in tests and early development).

    Returns:
        A node function ``(ALCState) -> dict``.
    """

    def node_memory_saver(state: ALCState) -> dict:
        """Persist session data to the database (side-effect only).

        Returns an empty dict — this node does not modify graph state.
        """
        student_id = state.get("student_id", 0)
        session_id = state.get("session_id")
        topic = state.get("current_topic", "General")
        diagnosis = state.get("latest_diagnosis", "")
        style = state.get("detected_learning_style", "unknown")
        summary = state.get("session_summary", "")
        skill_scores = state.get("skill_scores", {})
        topics_learned = state.get("topics_learned", [])
        topics_need_practice = state.get("topics_need_practice", [])

        if db_session is None:
            logger.info(
                "💾 [MEMORY] No DB session — skipping persistence. "
                "Student %s, topic=%s, style=%s",
                student_id,
                topic,
                style,
            )
            return {}

        try:
            # ── 1. Update session summary ─────────────────────────────
            from backend.app.models.session import Session as SessionModel

            if session_id:
                sess = db_session.get(SessionModel, session_id)
                if sess:
                    if summary:
                        sess.summary = summary
                    sess.ended_at = datetime.now(timezone.utc)
                    logger.info(
                        "💾 [MEMORY] Saved session summary for session_id=%s",
                        session_id,
                    )

            # ── 2. Update skill mastery scores ────────────────────────
            from backend.app.models.skill import Skill

            for skill_name, score in skill_scores.items():
                skill = (
                    db_session.query(Skill)
                    .filter_by(student_id=student_id, skill_name=skill_name)
                    .first()
                )
                if skill:
                    skill.mastery_score = max(0.0, min(100.0, float(score)))
                    skill.updated_at = datetime.now(timezone.utc)
            logger.info(
                "💾 [MEMORY] Updated skill scores for student %s: %s",
                student_id,
                skill_scores,
            )

            # ── 3. Store memory fragments ─────────────────────────────
            from backend.app.models.memory import Memory

            def _store_and_embed(mtype: str, content: str) -> None:
                """Write to SQLite and index in ChromaDB."""
                mem = Memory(student_id=student_id, memory_type=mtype, content=content)
                db_session.add(mem)
                db_session.flush()  # Assign mem.id before embedding
                try:
                    from backend.app.services.chroma_service import embed_memory
                    embed_memory(student_id, mtype, content, memory_id=mem.id)
                except Exception:
                    logger.debug("💾 [MEMORY] ChromaDB embed skipped for %s", mtype)

            if topics_need_practice:
                _store_and_embed(
                    "weakness",
                    f"Needs practice: {', '.join(topics_need_practice)}",
                )
            if topics_learned:
                _store_and_embed(
                    "strength",
                    f"Learned: {', '.join(topics_learned)}",
                )
            if style != "unknown":
                _store_and_embed(
                    "preference",
                    f"Preferred learning style: {style}",
                )
            if diagnosis:
                _store_and_embed(
                    "context",
                    f"Diagnosis: {diagnosis[:500]}",
                )
            logger.info(
                "💾 [MEMORY] Stored memory fragments for student %s",
                student_id,
            )

            db_session.commit()

        except Exception:
            logger.exception(
                "💾 [MEMORY] Error saving session data for student %s",
                student_id,
            )
            try:
                db_session.rollback()
            except Exception:
                pass

        return {}

    return node_memory_saver


# Convenience: a no-op saver for use when no DB is available.
node_memory_saver = make_memory_saver(db_session=None)
