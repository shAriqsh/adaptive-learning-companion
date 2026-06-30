"""LangGraph state definition for LearnMate AI.

This replaces the old root-level ``schema.py`` with a richer state that
tracks diagnosis, evaluation, reflection, and resource recommendations
across the full agent pipeline.
"""

from __future__ import annotations

from typing import Annotated, Literal

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class ALCState(TypedDict):
    """Shared state that flows through every node in the LangGraph."""

    # ── Core ──────────────────────────────────────────────────────────
    messages: Annotated[list, add_messages]
    student_id: int
    session_id: int | None

    # ── Topic Context ─────────────────────────────────────────────────
    current_topic: str
    current_difficulty: Literal["easy", "medium", "hard"]

    # ── Diagnosis ─────────────────────────────────────────────────────
    latest_diagnosis: str | None
    detected_learning_style: Literal[
        "visual", "analogical", "procedural", "unknown"
    ]
    skill_scores: dict  # {skill_name: mastery_score}

    # ── Question & Evaluation ─────────────────────────────────────────
    question_posed: str | None
    student_answer: str | None
    correct_answer: str | None
    is_answer_correct: bool | None
    evaluation_feedback: str | None

    # ── Reflection ────────────────────────────────────────────────────
    session_summary: str | None
    topics_learned: list[str]
    topics_need_practice: list[str]

    # ── Resources ─────────────────────────────────────────────────────
    recommended_resources: list[str]
    retrieved_memories: list[str]  # Populated by diagnostician via ChromaDB

    # ── Plan ──────────────────────────────────────────────────────────
    next_step: Literal["explain", "quiz", "evaluate", "reflect", "recommend"]
