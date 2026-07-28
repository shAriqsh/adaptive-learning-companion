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

# ── Thread tracking (lightweight — actual state lives in checkpointer) ────
# Maps student_id → db_session_id for the current active session.
# Conversation state (messages, diagnosis, etc.) is persisted by the
# SqliteSaver checkpointer and restored automatically per thread_id.
_active_threads: dict[int, int] = {}


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
    """Send a message to the AI tutor and receive a response.

    Conversation state is managed by LangGraph's ``SqliteSaver``
    checkpointer (STM).  Each student session gets a unique
    ``thread_id`` so the graph auto-saves/restores state per thread.
    """

    # ── Handle reset ──────────────────────────────────────────────────
    if request.reset:
        _active_threads.pop(request.student_id, None)
        return ChatResponse(
            response="Memory cleared. Ready for a new session!",
            current_topic="General",
            current_difficulty="easy",
            learning_style="unknown",
        )

    # ── Ensure student exists ─────────────────────────────────────────
    student = get_or_create_student(db, request.student_id)
    mastery = get_mastery_summary(db, student.id)

    # ── Get or create DB session → derive thread_id ───────────────────
    if student.id not in _active_threads:
        topic = request.topic or "General"
        db_sess = create_session(db, student.id, topic)
        _active_threads[student.id] = db_sess.id

    db_session_id = _active_threads[student.id]
    thread_id = f"student_{student.id}_session_{db_session_id}"

    # ── Build graph with checkpointer + store ─────────────────────────
    try:
        from backend.app.agents.graph import get_graph

        graph = get_graph(db_session=db)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialise agent graph: {exc}",
        )

    config = {"configurable": {"thread_id": thread_id}}

    # ── Retrieve checkpoint state for context ─────────────────────────
    # The checkpointer may already have state for this thread from a
    # previous turn.  We read it to detect answer intent and to
    # preserve fields like detected_learning_style across turns.
    try:
        snapshot = graph.get_state(config)
        checkpoint_values = snapshot.values if snapshot.values else {}
    except Exception:
        checkpoint_values = {}

    current_topic = request.topic or checkpoint_values.get(
        "current_topic", "General"
    )

    # ── Detect intent using checkpointed question state ───────────────
    is_answer = _detect_answer_intent(
        request.message,
        {"question_posed": checkpoint_values.get("question_posed")},
    )
    is_recommend = not is_answer and _detect_recommend_intent(request.message)

    if is_answer:
        next_step = "evaluate"
    elif is_recommend:
        next_step = "recommend"
    else:
        next_step = "explain"

    # ── Trim old messages if checkpoint exceeds limit ───────────────────
    # The checkpointer accumulates all messages.  When the history grows
    # past MESSAGE_HISTORY_LIMIT, we prepend RemoveMessage objects so the
    # add_messages reducer drops the oldest entries in this invocation.
    from backend.app.config import settings
    from langchain_core.messages import RemoveMessage

    checkpoint_msgs = checkpoint_values.get("messages", [])
    new_message = HumanMessage(content=request.message)

    if len(checkpoint_msgs) > settings.MESSAGE_HISTORY_LIMIT:
        msgs_to_remove = checkpoint_msgs[: -settings.MESSAGE_HISTORY_LIMIT]
        trim_removals = [
            RemoveMessage(id=m.id)
            for m in msgs_to_remove
            if hasattr(m, "id") and m.id
        ]
        input_messages = trim_removals + [new_message]
    else:
        input_messages = [new_message]

    # ── Build graph input ─────────────────────────────────────────────
    # Only the NEW message is passed — the checkpointer's add_messages
    # reducer appends it to the accumulated history automatically.
    # If trimming was needed, RemoveMessage objects precede the new msg.
    # Fields like detected_learning_style are preserved from the
    # checkpoint; skill_scores are refreshed from the DB each turn.
    graph_input = {
        "messages": input_messages,
        "student_id": student.id,
        "session_id": db_session_id,
        "current_topic": current_topic,
        "current_difficulty": checkpoint_values.get(
            "current_difficulty", "easy"
        ),
        "detected_learning_style": checkpoint_values.get(
            "detected_learning_style", "unknown"
        ),
        "latest_diagnosis": checkpoint_values.get("latest_diagnosis"),
        "skill_scores": mastery,
        "question_posed": (
            checkpoint_values.get("question_posed") if is_answer else None
        ),
        "student_answer": request.message if is_answer else None,
        "correct_answer": (
            checkpoint_values.get("correct_answer") if is_answer else None
        ),
        "is_answer_correct": None,
        "evaluation_feedback": None,
        "session_summary": None,
        "topics_learned": [],
        "topics_need_practice": [],
        "recommended_resources": [],
        "retrieved_memories": checkpoint_values.get(
            "retrieved_memories", []
        ),
        "next_step": next_step,
    }

    # ── Invoke graph (checkpointer auto-saves state per thread) ───────
    try:
        final_state = graph.invoke(graph_input, config=config)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}")

    # ── Clear question state in checkpoint after evaluation ───────────
    # Without this, the next turn would still see question_posed and
    # wrongly detect an answer intent.
    if is_answer:
        try:
            graph.update_state(
                config,
                {"question_posed": None, "correct_answer": None},
            )
        except Exception:
            pass  # non-critical

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

    # ── Persist messages to DB session (backward compat) ──────────────
    try:
        serialisable_msgs = [
            {"role": "human" if isinstance(m, HumanMessage) else "ai", "content": str(m.content)}
            for m in ai_messages
            if hasattr(m, "content")
        ]
        update_session(
            db,
            db_session_id,
            messages_json=json.dumps(serialisable_msgs, default=str),
        )
    except Exception:
        pass  # non-critical

    # ── Build response ────────────────────────────────────────────────
    raw_resources = final_state.get("recommended_resources", [])
    resources = raw_resources if raw_resources else None
    response_topic = final_state.get("current_topic", current_topic)

    return ChatResponse(
        response=last_response,
        current_topic=response_topic,
        current_difficulty=final_state.get("current_difficulty", "easy"),
        learning_style=final_state.get("detected_learning_style", "unknown"),
        mastery_score=mastery.get(response_topic),
        session_id=db_session_id,
        recommended_resources=resources,
    )
