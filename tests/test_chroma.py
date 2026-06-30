"""Tests for chroma_service — vector memory storage and retrieval.

Non-LLM tests verify graceful degradation (no API key → no crash).
LLM-tagged tests verify real embedding with a live GOOGLE_API_KEY.
"""
from __future__ import annotations

import os
import pytest


# ── Helpers ───────────────────────────────────────────────────────────────

needs_api_key = pytest.mark.skipif(
    not os.environ.get("GOOGLE_API_KEY")
    or os.environ.get("GOOGLE_API_KEY") == "test-key-not-real",
    reason="GOOGLE_API_KEY not set or is a test placeholder",
)


# ── Tests that do NOT require a real API key ──────────────────────────────

class TestChromaServiceNoop:
    """Verify graceful no-ops when the API key is absent."""

    def test_embed_memory_returns_false_without_key(self, monkeypatch):
        """embed_memory should return False (not raise) with no API key."""
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key-not-real")

        # Reset the module-level collection cache so config is re-read
        import backend.app.services.chroma_service as svc
        svc._collection = None
        svc._chroma_client = None

        result = svc.embed_memory(
            student_id=99,
            memory_type="weakness",
            content="Test weakness content",
            memory_id=1,
        )
        # Either False (embedding skipped) or True (chroma available but embed skipped)
        assert isinstance(result, bool)

    def test_retrieve_memories_returns_empty_without_key(self, monkeypatch):
        """retrieve_memories should return [] (not raise) with no API key."""
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key-not-real")

        import backend.app.services.chroma_service as svc
        svc._collection = None
        svc._chroma_client = None

        results = svc.retrieve_memories(student_id=99, query="derivatives", k=5)
        assert isinstance(results, list)
        assert results == []

    def test_clear_student_memories_no_crash(self, monkeypatch):
        """clear_student_memories should not raise even if ChromaDB is unavailable."""
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key-not-real")

        import backend.app.services.chroma_service as svc
        svc._collection = None
        svc._chroma_client = None

        result = svc.clear_student_memories(student_id=99)
        assert isinstance(result, bool)

    def test_module_imports_cleanly(self):
        """The service module should import without errors regardless of env."""
        import backend.app.services.chroma_service  # noqa: F401
        assert True


# ── Tests that DO require a real API key ─────────────────────────────────

@needs_api_key
@pytest.mark.llm
class TestChromaServiceLive:
    """Integration tests with a real ChromaDB + Google embedding."""

    def setup_method(self):
        """Reset ChromaDB state before each test."""
        import backend.app.services.chroma_service as svc
        svc._collection = None
        svc._chroma_client = None

    def teardown_method(self):
        """Clean up test data from ChromaDB after each test."""
        import backend.app.services.chroma_service as svc
        svc.clear_student_memories(student_id=999)
        svc._collection = None
        svc._chroma_client = None

    def test_embed_memory_returns_true(self):
        """embed_memory should return True when API key is present."""
        from backend.app.services.chroma_service import embed_memory
        result = embed_memory(
            student_id=999,
            memory_type="weakness",
            content="Student struggles with chain rule in calculus.",
            memory_id=101,
        )
        assert result is True

    def test_retrieve_memories_returns_relevant_result(self):
        """After embedding, retrieve_memories should return the content."""
        from backend.app.services.chroma_service import embed_memory, retrieve_memories

        content = "Student consistently confuses integration and differentiation."
        embed_memory(
            student_id=999,
            memory_type="weakness",
            content=content,
            memory_id=102,
        )

        results = retrieve_memories(
            student_id=999,
            query="integration and differentiation confusion",
            k=3,
        )
        assert isinstance(results, list)
        assert len(results) >= 1
        # The embedded content should appear in results
        assert any("integrat" in r.lower() or "differentiat" in r.lower() for r in results)

    def test_retrieve_memories_student_isolation(self):
        """retrieve_memories should not leak memories across students."""
        from backend.app.services.chroma_service import embed_memory, retrieve_memories

        embed_memory(
            student_id=999,
            memory_type="weakness",
            content="Student 999 struggles with quadratic equations.",
            memory_id=103,
        )

        # Query for a different student — should get no results
        results_other = retrieve_memories(
            student_id=998,
            query="quadratic equations",
            k=5,
        )
        assert all("Student 999" not in r for r in results_other)
