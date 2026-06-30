"""ChromaDB vector store service for LearnMate AI.

Provides semantic memory storage and retrieval using ChromaDB as the
vector store and Google's ``gemini-embedding-2`` model for embeddings.

All public functions degrade gracefully when:
- ``GOOGLE_API_KEY`` is absent (returns empty results / skips embed).
- ChromaDB is unavailable (logs a warning, no exception propagated).

This keeps the service safe to import in tests that don't set API keys.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

# ── ChromaDB client (module-level, lazy-initialised) ─────────────────────

_chroma_client = None
_collection = None


def _get_collection():
    """Lazily initialise the ChromaDB client and return the collection.

    Returns ``None`` if ChromaDB is unavailable.
    """
    global _chroma_client, _collection  # noqa: PLW0603

    if _collection is not None:
        return _collection

    try:
        import chromadb  # type: ignore[import-untyped]
        from chromadb.config import Settings as ChromaSettings  # type: ignore[import-untyped]

        from backend.app.config import settings

        chroma_path = settings.CHROMA_PATH
        os.makedirs(chroma_path, exist_ok=True)

        _chroma_client = chromadb.PersistentClient(
            path=chroma_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        _collection = _chroma_client.get_or_create_collection(
            name="student_memories",
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("🗄️  [CHROMA] Collection 'student_memories' ready at %s", chroma_path)
        return _collection

    except Exception:
        logger.warning("🗄️  [CHROMA] ChromaDB unavailable — vector memory disabled.", exc_info=True)
        return None


# ── Embedding function ────────────────────────────────────────────────────

def _get_embedding(text: str) -> list[float] | None:
    """Embed a single text string using Google's embedding model.

    Returns ``None`` when the API key is missing or embedding fails.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key or api_key == "test-key-not-real":
        return None

    try:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        embedder = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2")
        return embedder.embed_query(text)
    except Exception:
        logger.warning("🗄️  [CHROMA] Embedding failed for text snippet.", exc_info=True)
        return None


# ── Public API ────────────────────────────────────────────────────────────

def embed_memory(
    student_id: int,
    memory_type: str,
    content: str,
    memory_id: int | None = None,
) -> bool:
    """Embed and index a memory fragment in ChromaDB.

    Args:
        student_id: Owner of this memory.
        memory_type: e.g. ``"weakness"``, ``"strength"``, ``"preference"``,
            ``"context"``.
        content: Free-text description to embed.
        memory_id: Optional SQLite row ID to use as the ChromaDB document ID.
            If ``None``, a synthetic ID is generated.

    Returns:
        ``True`` if the memory was successfully stored, ``False`` otherwise.
    """
    collection = _get_collection()
    if collection is None:
        return False

    embedding = _get_embedding(content)
    if embedding is None:
        logger.debug("🗄️  [CHROMA] Skipping embed — no API key or embedding error.")
        return False

    doc_id = f"student_{student_id}_mem_{memory_id}" if memory_id else f"student_{student_id}_{memory_type}_{hash(content)}"

    try:
        collection.upsert(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[{"student_id": student_id, "memory_type": memory_type}],
        )
        logger.debug("🗄️  [CHROMA] Indexed memory id=%s for student %s", doc_id, student_id)
        return True
    except Exception:
        logger.warning("🗄️  [CHROMA] Failed to upsert memory.", exc_info=True)
        return False


def retrieve_memories(
    student_id: int,
    query: str,
    k: int = 5,
    memory_type: str | None = None,
) -> list[str]:
    """Retrieve the most relevant memories for a student via semantic search.

    Args:
        student_id: Filter results to this student.
        query: The query text to search against stored memories.
        k: Number of results to return.
        memory_type: Optional filter by memory type.

    Returns:
        A list of memory content strings, ordered by relevance.
        Returns an empty list if ChromaDB is unavailable or on any error.
    """
    collection = _get_collection()
    if collection is None:
        return []

    embedding = _get_embedding(query)
    if embedding is None:
        return []

    try:
        where: dict = {"student_id": student_id}
        if memory_type:
            where["memory_type"] = memory_type

        results = collection.query(
            query_embeddings=[embedding],
            n_results=k,
            where=where,
            include=["documents"],
        )
        docs: list[str] = results.get("documents", [[]])[0]
        logger.info(
            "🔍 [RAG] Retrieved %d memories for student %s (query=%r)",
            len(docs),
            student_id,
            query[:60],
        )
        return docs
    except Exception:
        logger.warning("🗄️  [CHROMA] Retrieval failed.", exc_info=True)
        return []


def clear_student_memories(student_id: int) -> bool:
    """Remove all indexed memories for a student (e.g., on account deletion).

    Returns:
        ``True`` on success, ``False`` if ChromaDB is unavailable.
    """
    collection = _get_collection()
    if collection is None:
        return False

    try:
        collection.delete(where={"student_id": student_id})
        logger.info("🗄️  [CHROMA] Cleared all memories for student %s", student_id)
        return True
    except Exception:
        logger.warning("🗄️  [CHROMA] Failed to clear student memories.", exc_info=True)
        return False
