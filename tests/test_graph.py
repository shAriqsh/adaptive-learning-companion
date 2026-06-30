"""V6: Graph — verify the LangGraph compiles and routing works correctly."""
import pytest

from backend.app.agents.graph import create_graph, get_graph


class TestGraphCompilation:
    def test_create_graph_no_db(self):
        """Graph compiles without a database session."""
        graph = create_graph(db_session=None)
        assert graph is not None

    def test_get_graph_cached(self):
        """get_graph() returns the same instance on repeated calls."""
        g1 = get_graph()
        g2 = get_graph()
        assert g1 is g2

    def test_get_graph_with_db_not_cached(self):
        """get_graph(db_session=X) always returns a fresh graph."""
        g1 = get_graph(db_session="fake")
        g2 = get_graph(db_session="fake")
        assert g1 is not g2


class TestGraphRouting:
    """Verify the conditional routing function dispatches correctly."""

    def test_route_explain(self):
        from backend.app.agents.graph import _should_continue_after_curriculum
        from langchain_core.messages import AIMessage
        state = {
            "messages": [AIMessage(content="Let me explain derivatives.")],
            "next_step": "explain",
        }
        assert _should_continue_after_curriculum(state) == "tutor"

    def test_route_quiz(self):
        from backend.app.agents.graph import _should_continue_after_curriculum
        from langchain_core.messages import AIMessage
        state = {
            "messages": [AIMessage(content="Time for a quiz!")],
            "next_step": "quiz",
        }
        assert _should_continue_after_curriculum(state) == "question_generator"

    def test_route_evaluate(self):
        from backend.app.agents.graph import _should_continue_after_curriculum
        from langchain_core.messages import AIMessage
        state = {
            "messages": [AIMessage(content="Let me check your answer.")],
            "next_step": "evaluate",
        }
        assert _should_continue_after_curriculum(state) == "evaluator"

    def test_route_reflect(self):
        from backend.app.agents.graph import _should_continue_after_curriculum
        from langchain_core.messages import AIMessage
        state = {
            "messages": [AIMessage(content="Let's reflect on this session.")],
            "next_step": "reflect",
        }
        assert _should_continue_after_curriculum(state) == "reflection"

    def test_route_tool_calls(self):
        from backend.app.agents.graph import _should_continue_after_curriculum
        from langchain_core.messages import AIMessage
        # Simulate a message with tool_calls
        msg = AIMessage(content="", tool_calls=[{"name": "execute_python_code", "args": {"code": "print(1)"}, "id": "tc1"}])
        state = {
            "messages": [msg],
            "next_step": "explain",
        }
        assert _should_continue_after_curriculum(state) == "tools"

    def test_route_recommend(self):
        from backend.app.agents.graph import _should_continue_after_curriculum
        from langchain_core.messages import AIMessage
        state = {
            "messages": [AIMessage(content="Please suggest some resources.")],
            "next_step": "recommend",
        }
        assert _should_continue_after_curriculum(state) == "recommend"

    def test_route_default_for_unknown(self):
        from backend.app.agents.graph import _should_continue_after_curriculum
        from langchain_core.messages import AIMessage
        state = {
            "messages": [AIMessage(content="Hello")],
            "next_step": "unknown_value",  # genuinely unknown → defaults to tutor
        }
        assert _should_continue_after_curriculum(state) == "tutor"
