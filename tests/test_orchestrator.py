"""Unit and integration tests for ChatOrchestrator."""

from unittest.mock import MagicMock
import pytest
from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage

from backend.app.orchestrator import ChatOrchestrator
from backend.app.schemas.chat import ChatRequest, ChatResponse
from backend.app.services.student_service import get_student


class TestChatOrchestratorIntentDetection:
    """Test private intent detection heuristics."""

    def test_detect_answer_intent_without_question(self):
        assert not ChatOrchestrator._detect_answer_intent(
            "42",
            {"question_posed": None},
        )
        assert not ChatOrchestrator._detect_answer_intent(
            "42",
            {},
        )

    def test_detect_answer_intent_with_valid_answer(self):
        session_data = {"question_posed": "What is 6 * 7?"}
        assert ChatOrchestrator._detect_answer_intent("42", session_data)
        assert ChatOrchestrator._detect_answer_intent("It is 42", session_data)
        assert ChatOrchestrator._detect_answer_intent("x = 5", session_data)

    def test_detect_answer_intent_with_topic_switch(self):
        session_data = {"question_posed": "What is 6 * 7?"}
        assert not ChatOrchestrator._detect_answer_intent(
            "explain derivatives instead",
            session_data,
        )
        assert not ChatOrchestrator._detect_answer_intent(
            "teach me calculus",
            session_data,
        )
        assert not ChatOrchestrator._detect_answer_intent(
            "what is a limit?",
            session_data,
        )

    @pytest.mark.parametrize(
        "msg",
        [
            "can you recommend some videos?",
            "where can i learn more about calculus?",
            "suggest resources please",
            "any good links?",
            "further reading on algebra",
        ],
    )
    def test_detect_recommend_intent_positive(self, msg: str):
        assert ChatOrchestrator._detect_recommend_intent(msg)

    @pytest.mark.parametrize(
        "msg",
        [
            "x = 5",
            "what is the derivative of x^2?",
            "I don't understand this problem",
        ],
    )
    def test_detect_recommend_intent_negative(self, msg: str):
        assert not ChatOrchestrator._detect_recommend_intent(msg)


class TestChatOrchestratorTrimmingAndExtraction:
    """Test message trimming and response extraction helpers."""

    def test_trim_messages_under_limit(self):
        new_msg = HumanMessage(content="Hello")
        msgs = [HumanMessage(id=f"m{i}", content=f"msg {i}") for i in range(5)]
        result = ChatOrchestrator._trim_messages(msgs, new_msg)
        assert result == [new_msg]

    def test_trim_messages_over_limit(self, monkeypatch):
        from backend.app.config import settings
        monkeypatch.setattr(settings, "MESSAGE_HISTORY_LIMIT", 3)

        new_msg = HumanMessage(content="Newest")
        msgs = [HumanMessage(id=f"m{i}", content=f"msg {i}") for i in range(5)]
        result = ChatOrchestrator._trim_messages(msgs, new_msg)

        # 5 items > limit 3 -> 2 RemoveMessage prepended
        assert len(result) == 3  # 2 RemoveMessage + 1 new_msg
        assert isinstance(result[0], RemoveMessage)
        assert result[0].id == "m0"
        assert isinstance(result[1], RemoveMessage)
        assert result[1].id == "m1"
        assert result[2] == new_msg

    def test_extract_response_skips_tool_calls(self):
        tool_call_msg = AIMessage(
            content="",
            tool_calls=[{"name": "fetch", "args": {}, "id": "call_1"}],
        )
        text_msg = AIMessage(content="Here is the explanation.")
        result = ChatOrchestrator._extract_response([tool_call_msg, text_msg])
        assert result == "Here is the explanation."


class TestChatOrchestratorHandle:
    """Test handle() method with isolated mock graph and real test database."""

    def test_handle_reset(self, db):
        orch = ChatOrchestrator()
        orch._active_threads[1] = 100

        req = ChatRequest(student_id=1, message="hello", reset=True)
        resp = orch.handle(req, db)

        assert 1 not in orch._active_threads
        assert "Memory cleared" in resp.response
        assert resp.current_topic == "General"

    def test_handle_direct_call_with_mock_graph(self, db):
        from backend.app.services.student_service import create_student

        student = create_student(db, name="TestStudent")
        mock_graph = MagicMock()
        mock_graph.get_state.return_value = MagicMock(values={})
        mock_graph.invoke.return_value = {
            "messages": [
                HumanMessage(content="What is a limit?"),
                AIMessage(content="A limit describes the behavior of a function near a point."),
            ],
            "current_topic": "Calculus",
            "current_difficulty": "medium",
            "detected_learning_style": "visual",
            "recommended_resources": [{"title": "Khan Academy Calculus", "url": "https://khanacademy.org"}],
        }

        orch = ChatOrchestrator(graph_factory=lambda db_session: mock_graph)
        req = ChatRequest(student_id=student.id, message="What is a limit?", topic="Calculus")
        resp = orch.handle(req, db)

        # Verify response
        assert isinstance(resp, ChatResponse)
        assert "limit describes the behavior" in resp.response
        assert resp.current_topic == "Calculus"
        assert resp.current_difficulty == "medium"
        assert resp.learning_style == "visual"
        assert resp.recommended_resources == [{"title": "Khan Academy Calculus", "url": "https://khanacademy.org"}]
        assert resp.session_id is not None

        # Verify DB student & session were tracked
        assert student.id in orch._active_threads

    def test_active_threads_isolation(self):
        orch1 = ChatOrchestrator()
        orch2 = ChatOrchestrator()
        orch1._active_threads[1] = 10
        assert 1 not in orch2._active_threads
