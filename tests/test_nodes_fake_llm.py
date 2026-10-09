"""Tests for agent nodes using injected deterministic FakeLLM (no API key required)."""

from langchain_core.messages import HumanMessage
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from backend.app.agents.nodes.curriculum import node_curriculum
from backend.app.agents.nodes.diagnostician import make_diagnostician, node_diagnose
from backend.app.agents.nodes.evaluator import node_evaluate
from backend.app.agents.nodes.question_generator import node_generate_question
from backend.app.agents.nodes.recommend import node_recommend
from backend.app.agents.nodes.reflection import node_reflect
from backend.app.agents.nodes.tutor import node_tutor


def _state(**overrides):
    base = {
        "messages": [HumanMessage(content="Explain quadratic formula.")],
        "student_id": 1,
        "session_id": 10,
        "current_topic": "Algebra",
        "current_difficulty": "medium",
        "skill_scores": {"Algebra": 50.0},
        "latest_diagnosis": "",
        "detected_learning_style": "unknown",
        "question_posed": None,
        "student_answer": None,
        "correct_answer": None,
        "is_answer_correct": None,
        "evaluation_feedback": None,
        "session_summary": None,
        "topics_learned": [],
        "topics_need_practice": [],
        "retrieved_memories": [],
        "next_step": None,
        "recommended_resources": [],
    }
    base.update(overrides)
    return base


class TestNodesWithFakeLLM:
    """Verify that nodes accept injected LLMs and produce expected deterministic output."""

    def test_diagnostician_with_injected_llm(self):
        fake = FakeListChatModel(responses=[
            "The student demonstrates visual learning tendencies and needs diagrams."
        ])
        diag_node = make_diagnostician(llm=fake)
        result = diag_node(_state())

        assert "visual learning" in result["latest_diagnosis"]
        assert result["detected_learning_style"] == "visual"

    def test_diagnostician_with_injected_memory_reader(self):
        from unittest.mock import MagicMock
        fake = FakeListChatModel(responses=[
            "Diagnosis based on prior weakness in fractions."
        ])
        fake_reader = MagicMock()
        fake_reader.retrieve.return_value = ["Needs practice: Fractions"]

        diag_node = make_diagnostician(llm=fake, memory_reader=fake_reader)
        result = diag_node(_state())

        fake_reader.retrieve.assert_called_once()
        assert result["retrieved_memories"] == ["Needs practice: Fractions"]
        assert "fractions" in result["latest_diagnosis"].lower()

    def test_evaluator_with_injected_llm(self):
        fake = FakeListChatModel(responses=[
            '{"correct": true, "explanation": "Excellent conceptual understanding."}'
        ])
        state = _state(
            student_answer="Because opposite angles are equal",
            correct_answer="Opposite angles are congruent",
            question_posed="Why are angles 1 and 2 equal?",
        )
        result = node_evaluate(state, llm=fake)

        assert result["is_answer_correct"] is True
        assert result["evaluation_feedback"] == "Excellent conceptual understanding."
        assert result["skill_scores"]["Algebra"] == 55.0

    def test_question_generator_with_injected_llm(self):
        fake = FakeListChatModel(responses=[
            '{"question": "Solve 2x + 4 = 10", "correct_answer": "3", "hint": "Subtract 4 first"}'
        ])
        result = node_generate_question(_state(), llm=fake)

        assert result["question_posed"] == "Solve 2x + 4 = 10"
        assert result["correct_answer"] == "3"
        assert len(result["messages"]) == 1
        assert "Solve 2x + 4 = 10" in result["messages"][0].content

    def test_tutor_with_injected_llm(self):
        fake = FakeListChatModel(responses=[
            "Let us break this problem down into visual steps."
        ])
        result = node_tutor(_state(), llm=fake)

        assert len(result["messages"]) == 1
        assert result["messages"][0].content == "Let us break this problem down into visual steps."

    def test_curriculum_with_injected_llm(self):
        fake = FakeListChatModel(responses=[
            "Tutor, please explain the concept of factoring polynomials."
        ])
        result = node_curriculum(_state(), llm=fake)

        assert result["next_step"] == "quiz"  # mastery >= 40
        assert len(result["messages"]) == 1
        assert "factoring polynomials" in result["messages"][0].content

    def test_reflection_with_injected_llm(self):
        fake = FakeListChatModel(responses=[
            '{"session_summary": "Mastered quadratic roots.", "topics_learned": ["Quadratics"], "topics_need_practice": ["Factoring"]}'
        ])
        result = node_reflect(_state(), llm=fake)

        assert result["session_summary"] == "Mastered quadratic roots."
        assert result["topics_learned"] == ["Quadratics"]
        assert result["topics_need_practice"] == ["Factoring"]

    def test_recommend_node_accepts_llm_parameter(self):
        fake = FakeListChatModel(responses=["not used"])
        result = node_recommend(_state(), llm=fake)
        assert "recommended_resources" in result
        assert "messages" in result
