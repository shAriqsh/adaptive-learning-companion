"""Service layer for student memory (preferences, weaknesses, etc.)."""

from sqlalchemy.orm import Session

from backend.app.models.memory import Memory


def store_memory(
    db: Session, student_id: int, memory_type: str, content: str
) -> Memory:
    """Create a new memory record for a student.

    Args:
        db: SQLAlchemy database session.
        student_id: The student this memory belongs to.
        memory_type: Category tag, e.g. ``"preference"``, ``"weakness"``,
            ``"misconception"``, ``"strength"``.
        content: Free-text description of the memory.

    Returns:
        The persisted Memory row.
    """
    memory = Memory(
        student_id=student_id,
        memory_type=memory_type,
        content=content,
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory


def get_memories(
    db: Session,
    student_id: int,
    memory_type: str | None = None,
    limit: int = 10,
) -> list[Memory]:
    """Retrieve recent memories for a student, optionally filtered by type.

    Args:
        db: SQLAlchemy database session.
        student_id: Owner of the memories.
        memory_type: If provided, only return memories of this type.
        limit: Maximum number of rows to return (default 10).

    Returns:
        A list of Memory rows, newest first.
    """
    query = db.query(Memory).filter(Memory.student_id == student_id)

    if memory_type is not None:
        query = query.filter(Memory.memory_type == memory_type)

    return query.order_by(Memory.created_at.desc()).limit(limit).all()


def get_all_preferences(db: Session, student_id: int) -> list[Memory]:
    """Shorthand for retrieving all ``preference`` memories."""
    return get_memories(db, student_id, memory_type="preference", limit=100)


def get_weaknesses(db: Session, student_id: int) -> list[Memory]:
    """Shorthand for retrieving all ``weakness`` memories."""
    return get_memories(db, student_id, memory_type="weakness", limit=100)
