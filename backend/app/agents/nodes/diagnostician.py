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

from dotenv import load_dotenv
from langchain_core.messages import SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from backend.app.agents.state import ALCState

load_dotenv(override=True)

logger = logging.getLogger(__name__)

llm = ChatGoogleGenerativeAI(
    model=os.getenv("LLM_MODEL", "gemini-2.0-flash"),
    temperature=0.7,
)

# How many recent messages to include in the diagnosis window.
_HISTORY_WINDOW = 5


def _extract_text(content) -> str:
    """Robustly extract text from LLM response content.

    Gemini sometimes returns a list of content blocks instead of a
    plain string.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and "text" in block
        )
    return str(content)


def _fetch_long_term_memories(
    student_id: int,
    topic: str,
    db_session=None,
    k: int = 5,
) -> list[str]:
    """Retrieve relevant long-term memories for RAG injection.

    Retrieval order:
    1. **LangGraph Store** — structured cross-thread memories (always tried).
    2. **ChromaDB** — semantic similarity retrieval (combined with Store).
    3. **SQLite** — fallback to recent memory rows if ChromaDB unavailable.

    Args:
        student_id: The student to retrieve memories for.
        topic: Used as the semantic query (most relevant to current session).
        db_session: Optional SQLAlchemy session for SQLite fallback.
        k: Max number of memories to retrieve.

    Returns:
        A list of memory content strings (may be empty).
    """
    memories: list[str] = []

    # ── 0. LangGraph Store (structured cross-thread memories) ─────────
    try:
        from langgraph.config import get_store

        store = get_store()
        if store is not None:
            ns = (f"student_{student_id}", "memories")
            for key in ("learning_style", "weaknesses", "strengths", "context"):
                item = store.get(ns, key)
                if item and item.value:
                    val = item.value
                    if key == "learning_style":
                        memories.append(
                            f"Preferred learning style: {val.get('style', 'unknown')}"
                        )
                    elif key == "weaknesses":
                        topics = val.get("topics", [])
                        if topics:
                            memories.append(
                                f"Needs practice: {', '.join(topics)}"
                            )
                    elif key == "strengths":
                        topics = val.get("topics", [])
                        if topics:
                            memories.append(
                                f"Learned: {', '.join(topics)}"
                            )
                    elif key == "context":
                        diag = val.get("diagnosis", "")
                        if diag:
                            memories.append(f"Prior diagnosis: {diag[:300]}")
            if memories:
                logger.info(
                    "🔍 [LTM] Injecting %d Store memories for student %s",
                    len(memories),
                    student_id,
                )
    except Exception:
        logger.debug("🔍 [LTM] Store retrieval skipped.", exc_info=True)

    # ── 1. ChromaDB semantic retrieval (combined with Store results) ──
    try:
        from backend.app.services.chroma_service import retrieve_memories
        results = retrieve_memories(student_id=student_id, query=topic, k=k)
        if results:
            logger.info(
                "🔍 [RAG] Injecting %d memories for student %s into diagnosis",
                len(results),
                student_id,
            )
            memories.extend(results)
            return memories
    except Exception:
        logger.debug("🔍 [RAG] ChromaDB retrieval skipped.", exc_info=True)

    # If Store returned results but ChromaDB didn't, still return them
    if memories:
        return memories

    # ── 2. SQLite fallback — get most recent memories ─────────────────
    if db_session is not None:
        try:
            from backend.app.services.memory_service import get_memories
            mems = get_memories(db_session, student_id, limit=k)
            return [m.content for m in mems]
        except Exception:
            logger.debug("🔍 [RAG] SQLite memory fallback failed.", exc_info=True)

    return []


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


def make_diagnostician(db_session=None):
    """Create a diagnostician node bound to a DB session.

    Uses the same closure pattern as ``make_memory_saver`` so the graph
    can inject a live DB session at request time without polluting state.

    Args:
        db_session: A SQLAlchemy ``Session``, or ``None`` for no-DB mode.

    Returns:
        A node function ``(ALCState) -> dict``.
    """

    def node_diagnose_with_db(state: ALCState) -> dict:
        student_id = state.get("student_id", 0)
        topic = state.get("current_topic", "General")
        skill_scores = state.get("skill_scores", {})
        current_mastery = skill_scores.get(topic, 0.0)
        current_style = state.get("detected_learning_style", "unknown")
        history = state["messages"][-_HISTORY_WINDOW:]

        # ── Fetch long-term memories for RAG ─────────────────────────
        long_term_memories = _fetch_long_term_memories(
            student_id=student_id,
            topic=topic,
            db_session=db_session,
            k=5,
        )

        prompt = _build_prompt(
            student_id=student_id,
            topic=topic,
            current_mastery=current_mastery,
            skill_scores=skill_scores,
            long_term_memories=long_term_memories,
        )

        analysis = llm.invoke([SystemMessage(content=prompt)] + history)
        content_text = _extract_text(analysis.content)

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
