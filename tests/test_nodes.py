"""V5: Agent Nodes — verify each node accepts a minimal state and returns without crashing.

These tests require a live LLM (GOOGLE_API_KEY must be set).
Mark them with @pytest.mark.llm so they can be skipped with `pytest -m "not llm"`.
"""
import os
import pytest

# Skip the entire module if no real API key is available
pytestmark = pytest.mark.llm

needs_api_key = pytest.mark.skipif(
    not os.environ.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_API_KEY") == "test-key-not-real",
    reason="GOOGLE_API_KEY not set or is a test placeholder"
)


def _minimal_state(**overrides) -> dict:
    """Build a minimal ALCState dict for testing."""
    from langchain_core.messages import HumanMessage
    base = {
        "messages": [HumanMessage(content="What is a derivative?")],
        "student_id": 1,
        "session_id": None,
        "current_topic": "Calculus",
        "current_difficulty": "easy",
        "latest_diagnosis": None,
        "detected_learning_style": "unknown",
        "skill_scores": {"Calculus": 30.0, "Limits": 20.0},
        "question_posed": None,
        "student_answer": None,
        "correct_answer": None,
        "is_answer_correct": None,
        "evaluation_feedback": None,
        "session_summary": None,
        "topics_learned": [],
        "topics_need_practice": [],
        "recommended_resources": [],
        "retrieved_memories": [],
        "next_step": "explain",
    }
    base.update(overrides)
    return base


@needs_api_key
class TestDiagnosticianNode:
    def test_returns_diagnosis(self):
        from backend.app.agents.nodes.diagnostician import node_diagnose
        result = node_diagnose(_minimal_state())
        assert "latest_diagnosis" in result
        assert isinstance(result["latest_diagnosis"], str)
        assert len(result["latest_diagnosis"]) > 0
        assert "detected_learning_style" in result


@needs_api_key
class TestCurriculumNode:
    def test_returns_messages(self):
        from backend.app.agents.nodes.curriculum import node_curriculum
        result = node_curriculum(_minimal_state())
        assert "messages" in result
        assert len(result["messages"]) > 0


@needs_api_key
class TestTutorNode:
    def test_returns_messages(self):
        from backend.app.agents.nodes.tutor import node_tutor
        result = node_tutor(_minimal_state())
        assert "messages" in result
        assert len(result["messages"]) > 0


@needs_api_key
class TestQuestionGeneratorNode:
    def test_returns_question(self):
        from backend.app.agents.nodes.question_generator import node_generate_question
        result = node_generate_question(_minimal_state())
        assert "question_posed" in result
        assert result["question_posed"] is not None
        assert "correct_answer" in result
        assert "current_difficulty" in result

    def test_easy_difficulty_for_low_mastery(self):
        from backend.app.agents.nodes.question_generator import node_generate_question
        result = node_generate_question(_minimal_state(skill_scores={"Calculus": 10.0}))
        assert result["current_difficulty"] == "easy"

    def test_hard_difficulty_for_high_mastery(self):
        from backend.app.agents.nodes.question_generator import node_generate_question
        result = node_generate_question(_minimal_state(skill_scores={"Calculus": 85.0}))
        assert result["current_difficulty"] == "hard"


@needs_api_key
class TestReflectionNode:
    def test_returns_summary(self):
        from backend.app.agents.nodes.reflection import node_reflect
        result = node_reflect(_minimal_state())
        assert "session_summary" in result
        assert isinstance(result["session_summary"], str)
        assert "topics_learned" in result
        assert "topics_need_practice" in result


class TestEvaluatorNode:
    """Evaluator with SymPy can run without LLM for math answers."""

    def test_correct_math_answer(self):
        from backend.app.agents.nodes.evaluator import node_evaluate
        state = _minimal_state(
            student_answer="2*x",
            correct_answer="2*x",
            question_posed="Find d/dx(x^2)",
        )
        result = node_evaluate(state)
        assert result["is_answer_correct"] is True

    def test_incorrect_math_answer(self):
        from backend.app.agents.nodes.evaluator import node_evaluate
        state = _minimal_state(
            student_answer="3*x",
            correct_answer="2*x",
            question_posed="Find d/dx(x^2)",
        )
        result = node_evaluate(state)
        assert result["is_answer_correct"] is False

    def test_mastery_increases_on_correct(self):
        from backend.app.agents.nodes.evaluator import node_evaluate
        state = _minimal_state(
            student_answer="2*x",
            correct_answer="2*x",
            skill_scores={"Calculus": 50.0},
        )
        result = node_evaluate(state)
        assert result["skill_scores"]["Calculus"] == 55.0  # +5

    def test_mastery_decreases_on_incorrect(self):
        from backend.app.agents.nodes.evaluator import node_evaluate
        state = _minimal_state(
            student_answer="3*x",
            correct_answer="2*x",
            skill_scores={"Calculus": 50.0},
        )
        result = node_evaluate(state)
        assert result["skill_scores"]["Calculus"] == 48.0  # -2

    def test_no_answer_returns_none(self):
        from backend.app.agents.nodes.evaluator import node_evaluate
        result = node_evaluate(_minimal_state())
        assert result.get("is_answer_correct") is None


class TestMemorySaverNode:
    def test_noop_without_db(self):
        from backend.app.agents.nodes.memory_saver import make_memory_saver
        saver = make_memory_saver(db_session=None)
        result = saver(_minimal_state())
        assert result == {}

    def test_persists_with_db(self, db):
        """Memory saver should persist skill scores and memory fragments."""
        from backend.app.agents.nodes.memory_saver import make_memory_saver
        from backend.app.services.student_service import create_student
        from backend.app.services.session_service import create_session
        from backend.app.models.skill import Skill
        from backend.app.models.memory import Memory

        # Set up a student with skills and a session
        student = create_student(db, name="MemSaverTest")
        sess = create_session(db, student.id, "Calculus")

        saver = make_memory_saver(db_session=db)
        state = _minimal_state(
            student_id=student.id,
            session_id=sess.id,
            current_topic="Calculus",
            skill_scores={"Limits": 75.0, "Derivatives": 30.0},
            topics_need_practice=["Derivatives"],
            topics_learned=["Limits"],
            session_summary="Covered limits and derivatives.",
            detected_learning_style="visual",
            latest_diagnosis="Student shows good understanding of limits.",
        )
        result = saver(state)
        assert result == {}

        # Verify skill scores were updated
        limits_skill = db.query(Skill).filter_by(
            student_id=student.id, skill_name="Limits"
        ).first()
        assert limits_skill is not None
        assert limits_skill.mastery_score == 75.0

        deriv_skill = db.query(Skill).filter_by(
            student_id=student.id, skill_name="Derivatives"
        ).first()
        assert deriv_skill is not None
        assert deriv_skill.mastery_score == 30.0

        # Verify memory fragments were stored
        memories = db.query(Memory).filter_by(student_id=student.id).all()
        memory_types = [m.memory_type for m in memories]
        assert "weakness" in memory_types
        assert "strength" in memory_types
        assert "preference" in memory_types
        assert "context" in memory_types

        # Verify session summary was saved
        db.refresh(sess)
        assert sess.summary == "Covered limits and derivatives."
        assert sess.ended_at is not None
