"""Tests for MemoryWriter, MemoryFacts, and persistence adapters."""

from unittest.mock import MagicMock
import pytest

from backend.app.memory.writer import (
    ChromaAdapter,
    MemoryFacts,
    MemoryWriter,
    SqliteAdapter,
    StoreAdapter,
)
from backend.app.models.memory import Memory
from backend.app.models.session import Session as SessionModel
from backend.app.models.skill import Skill
from backend.app.services.session_service import create_session
from backend.app.services.student_service import create_student


class TestMemoryFacts:
    """Test MemoryFacts construction and helper methods."""

    def test_default_values(self):
        facts = MemoryFacts()
        assert facts.session_id is None
        assert facts.topic == "General"
        assert facts.diagnosis == ""
        assert facts.style == "unknown"
        assert facts.summary == ""
        assert facts.skill_scores == {}
        assert facts.topics_learned == []
        assert facts.topics_need_practice == []

    def test_from_state(self):
        state = {
            "session_id": 42,
            "current_topic": "Calculus",
            "latest_diagnosis": "Needs help with derivatives",
            "detected_learning_style": "visual",
            "session_summary": "Good session on limits",
            "skill_scores": {"Limits": 80.0},
            "topics_learned": ["Limits"],
            "topics_need_practice": ["Derivatives"],
        }
        facts = MemoryFacts.from_state(state)
        assert facts.session_id == 42
        assert facts.topic == "Calculus"
        assert facts.diagnosis == "Needs help with derivatives"
        assert facts.style == "visual"
        assert facts.summary == "Good session on limits"
        assert facts.skill_scores == {"Limits": 80.0}
        assert facts.topics_learned == ["Limits"]
        assert facts.topics_need_practice == ["Derivatives"]
        # Dict access
        assert facts["session_id"] == 42
        assert facts.get("topic") == "Calculus"
        assert facts.get("non_existent", "fallback") == "fallback"


class TestMemoryWriterRoundTrip:
    """Integration and round-trip tests using the memory_writer fixture."""

    def test_round_trip_all_layers(self, db, memory_writer):
        # 1. Arrange student and session in DB
        student = create_student(db, name="Alice")
        sess = create_session(db, student.id, "Calculus")

        facts = MemoryFacts(
            session_id=sess.id,
            topic="Calculus",
            diagnosis="Student understands power rule but struggles with chain rule.",
            style="visual",
            summary="Completed calculus basics.",
            skill_scores={"Limits": 85.0, "Derivatives": 40.0},
            topics_learned=["Limits"],
            topics_need_practice=["Chain Rule"],
        )

        # 2. Act
        memory_writer.persist(student.id, facts)

        # 3. Assert SQLite (Session, Skill, Memory)
        db.refresh(sess)
        assert sess.summary == "Completed calculus basics."
        assert sess.ended_at is not None

        limits_skill = db.query(Skill).filter_by(student_id=student.id, skill_name="Limits").first()
        assert limits_skill is not None
        assert limits_skill.mastery_score == 85.0

        deriv_skill = db.query(Skill).filter_by(student_id=student.id, skill_name="Derivatives").first()
        assert deriv_skill is not None
        assert deriv_skill.mastery_score == 40.0

        memories = db.query(Memory).filter_by(student_id=student.id).all()
        types = {m.memory_type for m in memories}
        assert {"weakness", "strength", "preference", "context"}.issubset(types)

        # 4. Assert ChromaAdapter
        mock_embed = memory_writer._mock_embed
        assert mock_embed.call_count == 4
        call_types = {call.kwargs.get("memory_type") for call in mock_embed.call_args_list}
        assert call_types == {"weakness", "strength", "preference", "context"}

        # 5. Assert StoreAdapter
        store = memory_writer._test_store
        ns = (f"student_{student.id}", "memories")
        style_item = store.get(ns, "learning_style")
        assert style_item is not None
        assert style_item.value["style"] == "visual"

        weakness_item = store.get(ns, "weaknesses")
        assert weakness_item is not None
        assert weakness_item.value["topics"] == ["Chain Rule"]

        strength_item = store.get(ns, "strengths")
        assert strength_item is not None
        assert strength_item.value["topics"] == ["Limits"]

        context_item = store.get(ns, "context")
        assert context_item is not None
        assert "chain rule" in context_item.value["diagnosis"]

        summary_item = store.get(ns, f"session_summary_{sess.id}")
        assert summary_item is not None
        assert summary_item.value["summary"] == "Completed calculus basics."

    def test_persist_with_dict_facts(self, db, memory_writer):
        student = create_student(db, name="Bob")
        facts_dict = {
            "current_topic": "Algebra",
            "skill_scores": {"Linear Equations": 90.0},
            "topics_learned": ["Linear Equations"],
        }
        memory_writer.persist(student.id, facts_dict)

        skill = db.query(Skill).filter_by(student_id=student.id, skill_name="Linear Equations").first()
        assert skill is not None
        assert skill.mastery_score == 90.0

    def test_rollback_on_sqlite_error(self, db):
        bad_adapter = MagicMock()
        bad_adapter.write.side_effect = RuntimeError("Database disk full")
        writer = MemoryWriter(db_session=db, sqlite_adapter=bad_adapter)

        # Persist should catch and rollback without raising
        writer.persist(1, MemoryFacts())
        bad_adapter.write.assert_called_once()
