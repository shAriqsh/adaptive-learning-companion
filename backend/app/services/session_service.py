"""Service layer for tutoring session management."""

from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.models.session import Session as DBSession


def create_session(db: Session, student_id: int, topic: str) -> DBSession:
    """Start a new tutoring session.

    Args:
        db: SQLAlchemy database session.
        student_id: The student who owns this session.
        topic: Subject being studied.

    Returns:
        The newly created DBSession.
    """
    session = DBSession(student_id=student_id, topic=topic)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: Session, session_id: int) -> DBSession | None:
    """Fetch a single session by primary key."""
    return db.query(DBSession).filter(DBSession.id == session_id).first()


def update_session(
    db: Session,
    session_id: int,
    *,
    summary: str | None = None,
    messages_json: str | None = None,
    ended_at: datetime | None = None,
) -> DBSession | None:
    """Patch mutable fields on an existing session.

    Only provided (non-None) keyword arguments are applied.

    Args:
        db: SQLAlchemy database session.
        session_id: PK of the session to update.
        summary: Optional session summary text.
        messages_json: Optional JSON-serialized message history.
        ended_at: Optional timestamp marking session end.

    Returns:
        The updated DBSession, or None if not found.
    """
    session = get_session(db, session_id)
    if session is None:
        return None

    if summary is not None:
        session.summary = summary
    if messages_json is not None:
        session.messages_json = messages_json
    if ended_at is not None:
        session.ended_at = ended_at

    db.commit()
    db.refresh(session)
    return session


def get_student_sessions(
    db: Session, student_id: int, limit: int = 20
) -> list[DBSession]:
    """Return the most recent sessions for a student.

    Args:
        db: SQLAlchemy database session.
        student_id: Owner of the sessions.
        limit: Maximum number of sessions to return (default 20).

    Returns:
        A list of DBSession rows, newest first.
    """
    return (
        db.query(DBSession)
        .filter(DBSession.student_id == student_id)
        .order_by(DBSession.started_at.desc())
        .limit(limit)
        .all()
    )


def get_session_count(db: Session, student_id: int) -> int:
    """Return total number of sessions for a student."""
    return (
        db.query(func.count(DBSession.id))
        .filter(DBSession.student_id == student_id)
        .scalar()
        or 0
    )
