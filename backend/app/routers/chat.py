"""Chat router — main conversational endpoint for the AI tutor."""
from __future__ import annotations

import json
import re
from typing import Any

try:
    from langsmith import traceable
except ImportError:  # graceful fallback if langsmith not installed
    def traceable(**kwargs):  # type: ignore[misc]
        def decorator(fn):  # type: ignore[misc]
            return fn
        return decorator

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy.orm import Session as DBSession

from backend.app.database import get_db
from backend.app.schemas.chat import ChatRequest, ChatResponse
from backend.app.services.student_service import get_or_create_student
from backend.app.services.skill_service import get_mastery_summary
from backend.app.services.session_service import (
    create_session,
    get_session,
    update_session,
)

router = APIRouter(prefix="/chat", tags=["Chat"])

# ── In-memory session store (per-process, lost on restart) ────────────────
# Maps student_id -> {messages, current_topic, ...}
_active_sessions: dict[int, dict[str, Any]] = {}


def _get_session_data(student_id: int) -> dict[str, Any]:
    """Retrieve or initialise the in-memory session context."""
    if student_id not in _active_sessions:
        _active_sessions[student_id] = {
            "messages": [],
            "current_topic": "General",
            "detected_learning_style": "unknown",
            "latest_diagnosis": None,
            "db_session_id": None,
            "question_posed": None,
            "correct_answer": None,
        }
    return _active_sessions[student_id]


def _detect_answer_intent(message: str, session_data: dict) -> bool:
    """Heuristically decide if a user message is an answer to a posed question.

    Returns True if a question was previously posed and the message
    looks like an answer rather than a new topic request.
    """
    if not session_data.get("question_posed"):
        return False

    # If the message is short-ish and doesn't ask a new question, it's likely an answer
    msg_lower = message.strip().lower()
    new_topic_signals = ["teach me", "explain", "what is", "how do", "help me with", "let's learn", "move on to"]
    for signal in new_topic_signals:
        if msg_lower.startswith(signal):
            return False

    return True


def _detect_recommend_intent(message: str) -> bool:
    """Return True if the student is asking for resource recommendations."""
    msg_lower = message.strip().lower()
    recommend_signals = [
        "recommend", "resources", "suggest", "where can i learn",
        "videos", "articles", "links", "more about", "further reading",
        "what should i read", "any good",
    ]
    return any(signal in msg_lower for signal in recommend_signals)


@router.post("", response_model=ChatResponse)
@traceable(name="chat_endpoint", run_type="chain")
async def chat(request: ChatRequest, db: DBSession = Depends(get_db)):
    """Send a message to the AI tutor and receive a response."""

    # ── Handle reset ──────────────────────────────────────────────────
    if request.reset:
        _active_sessions.pop(request.student_id, None)
        return ChatResponse(
            response="Memory cleared. Ready for a new session!",
            current_topic="General",
            current_difficulty="easy",
            learning_style="unknown",
        )

    # ── Ensure student exists ─────────────────────────────────────────
    student = get_or_create_student(db, request.student_id)
    mastery = get_mastery_summary(db, student.id)

    # ── Retrieve / create in-memory session ───────────────────────────
    session_data = _get_session_data(student.id)
    history: list = session_data["messages"]

    # Create a DB session record on first message
    if session_data["db_session_id"] is None:
        topic = request.topic or session_data["current_topic"]
        db_sess = create_session(db, student.id, topic)
        session_data["db_session_id"] = db_sess.id

    # Override topic if provided
    if request.topic:
        session_data["current_topic"] = request.topic

    # Append user message
    history.append(HumanMessage(content=request.message))

    # ── Detect if this is an answer submission ────────────────────────
    is_answer = _detect_answer_intent(request.message, session_data)
    is_recommend = not is_answer and _detect_recommend_intent(request.message)

    # ── Build graph input state ───────────────────────────────────────
    try:
        from backend.app.agents.graph import get_graph

        # Use a per-request graph with the real DB session for persistence
        graph = get_graph(db_session=db)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialise agent graph: {exc}",
        )

    if is_answer:
        next_step = "evaluate"
    elif is_recommend:
        next_step = "recommend"
    else:
        next_step = "explain"

    graph_input = {
        "messages": history,
        "student_id": student.id,
        "session_id": session_data["db_session_id"],
        "current_topic": session_data["current_topic"],
        "current_difficulty": "easy",
        "detected_learning_style": session_data["detected_learning_style"],
        "latest_diagnosis": session_data["latest_diagnosis"],
        "skill_scores": mastery,
        "question_posed": session_data.get("question_posed") if is_answer else None,
        "student_answer": request.message if is_answer else None,
        "correct_answer": session_data.get("correct_answer") if is_answer else None,
        "is_answer_correct": None,
        "evaluation_feedback": None,
        "session_summary": None,
        "topics_learned": [],
        "topics_need_practice": [],
        "recommended_resources": [],
        "retrieved_memories": [],
        "next_step": next_step,
    }

    try:
        final_state = graph.invoke(graph_input)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}")

    # ── Extract AI response ───────────────────────────────────────────
    ai_messages = final_state.get("messages", [])
    last_response = "I'm having trouble thinking right now."

    for msg in reversed(ai_messages):
        if isinstance(msg, AIMessage) and msg.content and not getattr(msg, "tool_calls", None):
            if isinstance(msg.content, list):
                last_response = "\n".join(
                    block.get("text", "")
                    for block in msg.content
                    if isinstance(block, dict) and "text" in block
                )
            else:
                last_response = msg.content
            break

    # ── Update in-memory session ──────────────────────────────────────
    session_data["messages"] = ai_messages
    session_data["current_topic"] = final_state.get("current_topic", session_data["current_topic"])
    session_data["detected_learning_style"] = final_state.get(
        "detected_learning_style", session_data["detected_learning_style"]
    )
    session_data["latest_diagnosis"] = final_state.get("latest_diagnosis")

    # Track question state for answer detection on next turn
    session_data["question_posed"] = final_state.get("question_posed")
    session_data["correct_answer"] = final_state.get("correct_answer")

    # Clear answer fields after evaluation so they don't persist
    if is_answer:
        session_data["question_posed"] = None
        session_data["correct_answer"] = None

    # Persist messages to DB session
    try:
        serialisable_msgs = [
            {"role": "human" if isinstance(m, HumanMessage) else "ai", "content": str(m.content)}
            for m in ai_messages
            if hasattr(m, "content")
        ]
        update_session(
            db,
            session_data["db_session_id"],
            messages_json=json.dumps(serialisable_msgs, default=str),
        )
    except Exception:
        pass  # non-critical

    # ── Extract recommended resources ───────────────────────────────────
    raw_resources = final_state.get("recommended_resources", [])
    resources = raw_resources if raw_resources else None

    return ChatResponse(
        response=last_response,
        current_topic=session_data["current_topic"],
        current_difficulty=final_state.get("current_difficulty", "easy"),
        learning_style=session_data["detected_learning_style"],
        mastery_score=mastery.get(session_data["current_topic"]),
        session_id=session_data["db_session_id"],
        recommended_resources=resources,
    )
