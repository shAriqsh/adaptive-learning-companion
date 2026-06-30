from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class Skill(Base):
    """A node in the per-student skill tree (self-referential adjacency list)."""

    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    skill_name: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_skill_id: Mapped[int | None] = mapped_column(
        ForeignKey("skills.id"),
        nullable=True,
    )
    mastery_score: Mapped[float] = mapped_column(default=0.0)
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ─────────────────────────────────────────────────
    student: Mapped[Student] = relationship(back_populates="skills")

    children: Mapped[list[Skill]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    parent: Mapped[Skill | None] = relationship(
        back_populates="children",
        remote_side=[id],
        lazy="selectin",
    )
