"""Diagnostician node — analyses the student's understanding.

Phase 3 upgrade:
- Converted to a factory ``make_diagnostician(db_session)`` so it can
  receive a live DB session for RAG memory retrieval.
- Before building the LLM prompt, it fetches the student's most
  relevant past memories from ChromaDB (semantic) and SQLite (recent).
- Injects these under a 'Student Long-Term Memory' section in the prompt.
- The no-arg ``node_diagnose`` function is kept for backward compatibility
  (used in tests and the no-DB graph path).
"""

from __future__ import annotations

import logging
import os

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage

from backend.app.agents.state import ALCState
from backend.app.llm import get_llm
from backend.app.memory.reader import MemoryReader
from backend.app.utils.content import extract_text

logger = logging.getLogger(__name__)

# How many recent messages to include in the diagnosis window.
_HISTORY_WINDOW = 5





def _fetch_long_term_memories(
    student_id: int,
    topic: str,
    db_session=None,
    k: int = 5,
    memory_reader: MemoryReader | None = None,
) -> list[str]:
    """Retrieve relevant long-term memories for RAG injection via MemoryReader."""
    reader = memory_reader or MemoryReader(db_session=db_session)
    return reader.retrieve(student_id=student_id, query=topic, k=k)


def _build_prompt(
    student_id: int,
    topic: str,
    current_mastery: float,
    skill_scores: dict,
    long_term_memories: list[str],
) -> str:
    """Build the diagnostician system prompt with optional memory context."""
    memory_section = ""
    if long_term_memories:
        formatted = "\n".join(f"  - {m}" for m in long_term_memories)
        memory_section = f"""
Student Long-Term Memory (from previous sessions):
{formatted}

Use this context to inform your diagnosis — e.g. recurring weaknesses,
preferred learning style, topics already mastered.
"""

    return f"""You are the Diagnostician for an adaptive learning system.

Student ID: {student_id}
Topic: {topic}
Current Mastery Score: {current_mastery}/100
Known Skill Scores: {skill_scores}
{memory_section}
Analyse the student's recent messages and produce a structured diagnosis.
Your output MUST include each of the following sections:

1. **Concept Being Discussed**: What specific concept is the student working on?
2. **Confidence Level**: A float from 0.0 to 1.0 indicating how confident the student seems.
3. **Understanding Status**: Is the student grasping the material, struggling, or somewhere in between?
4. **Identified Misconceptions**: List any wrong assumptions or errors the student has shown.
5. **Prerequisite Gaps**: Are there foundational topics the student seems to be missing?
6. **Learning Style Indicators**: Based on the student's language and preferences, do they seem to prefer:
   - *visual*: diagrams, graphs, step-by-step visual breakdowns
   - *analogical*: real-world examples and analogies
   - *procedural*: numbered step-by-step methods and algorithms
   - *unknown*: not enough data yet

Be specific and evidence-based — cite the student's own words where possible.
"""


def make_diagnostician(
    db_session=None,
    llm: BaseChatModel | None = None,
    memory_reader: MemoryReader | None = None,
):
    """Create a diagnostician node bound to a DB session, LLM, and MemoryReader.

    Uses the same closure pattern as ``make_memory_saver`` so the graph
    can inject a live DB session at request time without polluting state.

    Args:
        db_session: A SQLAlchemy ``Session``, or ``None`` for no-DB mode.
        llm: A ``BaseChatModel`` instance, or ``None`` to use ``get_llm("diagnostician")``.
        memory_reader: A ``MemoryReader`` instance, or ``None`` to use default reader.

    Returns:
        A node function ``(ALCState) -> dict``.
    """
    bound_llm = llm if llm is not None else get_llm("diagnostician")
    reader = memory_reader if memory_reader is not None else MemoryReader(db_session=db_session)

    def node_diagnose_with_db(
        state: ALCState,
        llm: BaseChatModel | None = None,
        memory_reader: MemoryReader | None = None,
    ) -> dict:
        active_llm = llm or bound_llm
        active_reader = memory_reader or reader
        student_id = state.get("student_id", 0)
        topic = state.get("current_topic", "General")
        skill_scores = state.get("skill_scores", {})
        current_mastery = skill_scores.get(topic, 0.0)
        current_style = state.get("detected_learning_style", "unknown")
        history = state["messages"][-_HISTORY_WINDOW:]

        # ── Fetch long-term memories for RAG ─────────────────────────
        long_term_memories = active_reader.retrieve(
            student_id=student_id,
            query=topic,
            k=5,
        )

        prompt = _build_prompt(
            student_id=student_id,
            topic=topic,
            current_mastery=current_mastery,
            skill_scores=skill_scores,
            long_term_memories=long_term_memories,
        )

        analysis = active_llm.invoke([SystemMessage(content=prompt)] + history)
        content_text = extract_text(analysis.content)

        # Improved learning style detection via keyword scoring
        detected_style = current_style
        content_lower = content_text.lower()

        # Score each style by how many indicator words appear
        style_indicators = {
            "visual": [
                "visual", "diagram", "chart", "graph", "picture",
                "image", "draw", "illustration", "see", "show me",
            ],
            "analogical": [
                "analogical", "analogy", "like", "similar to",
                "compare", "metaphor", "relate", "connection",
            ],
            "procedural": [
                "procedural", "step-by-step", "step by step",
                "procedure", "algorithm", "method", "process",
                "sequential", "follow the steps",
            ],
        }

        best_style = None
        best_score = 0
        for style, keywords in style_indicators.items():
            score = sum(1 for kw in keywords if kw in content_lower)
            if score > best_score:
                best_score = score
                best_style = style

        if best_score >= 2:
            detected_style = best_style  # type: ignore[assignment]
        elif best_score == 1 and current_style == "unknown":
            detected_style = best_style  # type: ignore[assignment]

        logger.info(
            "🕵️ [DIAGNOSIS] Student %s: %s...",
            student_id,
            content_text[:120],
        )

        return {
            "latest_diagnosis": content_text,
            "detected_learning_style": detected_style,
            "retrieved_memories": long_term_memories,
        }

    return node_diagnose_with_db


# ── Convenience: no-DB node (backward compat + tests) ────────────────────

node_diagnose = make_diagnostician(db_session=None)
