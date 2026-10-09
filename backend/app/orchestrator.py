"""Chat Orchestrator — coordinates state, intent, graph invocation, and persistence.

Encapsulates conversation orchestration away from HTTP routing, enabling clean
testing without FastAPI TestClient.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from fastapi import HTTPException
from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage
from sqlalchemy.orm import Session as DBSession

from backend.app.config import settings
from backend.app.schemas.chat import ChatRequest, ChatResponse
from backend.app.services.session_service import create_session, update_session
from backend.app.services.skill_service import get_mastery_summary
from backend.app.services.student_service import get_or_create_student
from backend.app.utils.content import extract_text

logger = logging.getLogger(__name__)


class ChatOrchestrator:
    """Orchestrates turn-by-turn conversational flow between user, graph, and database."""

    def __init__(self, graph_factory: Callable[..., Any] | None = None) -> None:
        """Initialize the orchestrator with an optional graph factory.

        Args:
            graph_factory: Callable returning a compiled LangGraph StateGraph.
                           If None, lazily imports and calls ``get_graph``.
        """
        self.graph_factory = graph_factory
        # Instance-level session thread tracking: student_id -> db_session_id
        self._active_threads: dict[int, int] = {}

    @staticmethod
    def _detect_answer_intent(message: str, session_data: dict[str, Any]) -> bool:
        """Heuristically decide if a user message is an answer to a posed question."""
        if not session_data.get("question_posed"):
            return False

        msg_lower = message.strip().lower()
        new_topic_signals = [
            "teach me",
            "explain",
            "what is",
            "how do",
            "help me with",
            "let's learn",
            "move on to",
        ]
        for signal in new_topic_signals:
            if msg_lower.startswith(signal):
                return False

        return True

    @staticmethod
    def _detect_recommend_intent(message: str) -> bool:
        """Return True if the student is asking for resource recommendations."""
        msg_lower = message.strip().lower()
        recommend_signals = [
            "recommend",
            "resources",
            "suggest",
            "where can i learn",
            "videos",
            "articles",
            "links",
            "more about",
            "further reading",
            "what should i read",
            "any good",
        ]
        return any(signal in msg_lower for signal in recommend_signals)

    @staticmethod
    def _trim_messages(
        checkpoint_msgs: list[Any],
        new_message: HumanMessage,
    ) -> list[Any]:
        """Prepend RemoveMessage objects if conversation history exceeds limit."""
        if len(checkpoint_msgs) > settings.MESSAGE_HISTORY_LIMIT:
            msgs_to_remove = checkpoint_msgs[: -settings.MESSAGE_HISTORY_LIMIT]
            trim_removals = [
                RemoveMessage(id=m.id)
                for m in msgs_to_remove
                if hasattr(m, "id") and m.id
            ]
            return trim_removals + [new_message]
        return [new_message]

    @staticmethod
    def _extract_response(ai_messages: list[Any]) -> str:
        """Extract latest AI text response from message history."""
        last_response = "I'm having trouble thinking right now."
        for msg in reversed(ai_messages):
            if (
                isinstance(msg, AIMessage)
                and msg.content
                and not getattr(msg, "tool_calls", None)
            ):
                last_response = extract_text(msg.content)
                break
        return last_response

    def handle(self, request: ChatRequest, db: DBSession) -> ChatResponse:
        """Process a chat request, invoke the agent graph, and persist results.

        Args:
            request: Inbound chat payload.
            db: Active database session.

        Returns:
            Formatted ChatResponse for the student.
        """
        # 1. Handle reset
        if request.reset:
            self._active_threads.pop(request.student_id, None)
            return ChatResponse(
                response="Memory cleared. Ready for a new session!",
                current_topic="General",
                current_difficulty="easy",
                learning_style="unknown",
            )

        # 2. Ensure student exists & fetch current mastery
        student = get_or_create_student(db, request.student_id)
        mastery = get_mastery_summary(db, student.id)

        # 3. Get or create DB session → derive thread_id
        if student.id not in self._active_threads:
            topic = request.topic or "General"
            db_sess = create_session(db, student.id, topic)
            self._active_threads[student.id] = db_sess.id

        db_session_id = self._active_threads[student.id]
        thread_id = f"student_{student.id}_session_{db_session_id}"

        # 4. Build graph with checkpointer + store
        try:
            if self.graph_factory is not None:
                graph = self.graph_factory(db_session=db)
            else:
                from backend.app.agents.graph import get_graph

                graph = get_graph(db_session=db)
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialise agent graph: {exc}",
            ) from exc

        config = {"configurable": {"thread_id": thread_id}}

        # 5. Retrieve checkpoint state for context
        try:
            snapshot = graph.get_state(config)
            checkpoint_values = snapshot.values if snapshot.values else {}
        except Exception:
            checkpoint_values = {}

        current_topic = request.topic or checkpoint_values.get(
            "current_topic", "General"
        )

        # 6. Detect intent using checkpointed question state
        is_answer = self._detect_answer_intent(
            request.message,
            {"question_posed": checkpoint_values.get("question_posed")},
        )
        is_recommend = not is_answer and self._detect_recommend_intent(request.message)

        if is_answer:
            next_step = "evaluate"
        elif is_recommend:
            next_step = "recommend"
        else:
            next_step = "explain"

        # 7. Build graph input with trimmed history
        new_message = HumanMessage(content=request.message)
        input_messages = self._trim_messages(
            checkpoint_values.get("messages", []),
            new_message,
        )

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

        # 8. Invoke graph
        try:
            final_state = graph.invoke(graph_input, config=config)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Agent error: {exc}") from exc

        # 9. Clear question state in checkpoint after evaluation
        if is_answer:
            try:
                graph.update_state(
                    config,
                    {"question_posed": None, "correct_answer": None},
                )
            except Exception:
                pass

        # 10. Extract AI response
        ai_messages = final_state.get("messages", [])
        last_response = self._extract_response(ai_messages)

        # 11. Persist messages to DB session
        try:
            serialisable_msgs = [
                {
                    "role": "human" if isinstance(m, HumanMessage) else "ai",
                    "content": str(m.content),
                }
                for m in ai_messages
                if hasattr(m, "content")
            ]
            update_session(
                db,
                db_session_id,
                messages_json=json.dumps(serialisable_msgs, default=str),
            )
        except Exception:
            pass

        # 12. Build response
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
