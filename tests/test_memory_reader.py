"""Tests for MemoryReader, multi-tier retrieval, deduplication, and degradation."""

from unittest.mock import MagicMock
import pytest

from backend.app.memory.reader import MemoryReader
from backend.app.memory.writer import MemoryFacts
from backend.app.services.student_service import create_student
from backend.app.services.session_service import create_session


class TestMemoryReader:
    """Unit and integration tests for MemoryReader."""

    def test_deduplication_preserves_order(self):
        """Duplicates across backends should be removed while preserving order."""
        fake_store = MagicMock()
        fake_store.get.side_effect = lambda ns, key: {
            "learning_style": MagicMock(value={"style": "visual"}),
            "weaknesses": MagicMock(value={"topics": ["Derivatives"]}),
        }.get(key)

        def mock_chroma(student_id, query, k):
            return ["Needs practice: Derivatives", "Semantic topic match"]

        fake_db = MagicMock()
        # Mock get_memories returning duplicates
        mem1 = MagicMock(content="Needs practice: Derivatives")
        mem2 = MagicMock(content="Relational fragment")
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "backend.app.services.memory_service.get_memories",
                lambda db, student_id, limit: [mem1, mem2],
            )
            reader = MemoryReader(
                db_session=fake_db,
                chroma_service=mock_chroma,
                store=fake_store,
            )
            results = reader.retrieve(student_id=1, query="Calculus", k=10)

        # "Needs practice: Derivatives" appears in Store, Chroma, and SQLite,
        # but must appear only once in the final output.
        assert results.count("Needs practice: Derivatives") == 1
        assert "Preferred learning style: visual" in results
        assert "Semantic topic match" in results
        assert "Relational fragment" in results
        assert len(results) == 4

    def test_respects_limit_k(self):
        """Should truncate output to k items when k is specified."""
        mock_chroma = lambda student_id, query, k: [f"Item {i}" for i in range(10)]
        reader = MemoryReader(chroma_service=mock_chroma)
        results = reader.retrieve(student_id=1, query="test", k=3)
        assert len(results) == 3
        assert results == ["Item 0", "Item 1", "Item 2"]

    def test_graceful_degradation_on_chroma_failure(self):
        """If ChromaDB fails or raises an exception, Store and SQLite still return."""
        bad_chroma = MagicMock(side_effect=RuntimeError("Chroma unavailable"))
        fake_store = MagicMock()
        fake_store.get.return_value = MagicMock(value={"style": "procedural"})

        reader = MemoryReader(chroma_service=bad_chroma, store=fake_store)
        results = reader.retrieve(student_id=1, query="Calculus", k=5)

        assert results == ["Preferred learning style: procedural"]

    def test_graceful_degradation_on_store_failure(self):
        """If LangGraph Store fails, Chroma still returns results."""
        bad_store = MagicMock()
        bad_store.get.side_effect = RuntimeError("Store timeout")

        reader = MemoryReader(
            chroma_service=lambda s, q, k: ["Semantic memory 1"],
            store=bad_store,
        )
        results = reader.retrieve(student_id=1, query="Calculus", k=5)

        assert results == ["Semantic memory 1"]

    def test_graceful_degradation_on_sqlite_failure(self):
        """If SQLite fails, Chroma and Store results are preserved."""
        fake_store = MagicMock()
        fake_store.get.side_effect = (
            lambda ns, k: MagicMock(value={"topics": ["Limits"]})
            if k == "weaknesses"
            else None
        )

        bad_db = MagicMock()
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "backend.app.services.memory_service.get_memories",
                MagicMock(side_effect=RuntimeError("DB disconnected")),
            )
            reader = MemoryReader(
                db_session=bad_db,
                chroma_service=MagicMock(return_value=[]),
                store=fake_store,
            )
            results = reader.retrieve(student_id=1, query="Calculus", k=5)

        assert results == ["Needs practice: Limits"]


class TestMemoryWriterReaderRoundTrip:
    """Round-trip verification using the memory_writer and memory_reader fixtures."""

    def test_writer_persist_and_reader_retrieve(self, db, memory_writer, memory_reader):
        # 1. Arrange test student and session
        student = create_student(db, name="Charlie")
        sess = create_session(db, student.id, "Calculus")

        facts = MemoryFacts(
            session_id=sess.id,
            topic="Calculus",
            diagnosis="Student struggles with chain rule but mastered power rule.",
            style="visual",
            summary="Covered derivatives foundations.",
            skill_scores={"Limits": 90.0, "Derivatives": 45.0},
            topics_learned=["Power Rule"],
            topics_need_practice=["Chain Rule"],
        )

        # 2. Write via MemoryWriter (Ticket 02)
        memory_writer.persist(student.id, facts)

        # 3. Read via MemoryReader (Ticket 03)
        retrieved = memory_reader.retrieve(student_id=student.id, query="Calculus", k=10)

        # 4. Assert
        assert len(retrieved) > 0
        retrieved_text = " ".join(retrieved)

        # Check learning style was retrieved
        assert "visual" in retrieved_text.lower()
        # Check weaknesses were retrieved
        assert "chain rule" in retrieved_text.lower()
        # Check strengths were retrieved
        assert "power rule" in retrieved_text.lower()
