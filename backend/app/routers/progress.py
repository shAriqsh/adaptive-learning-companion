"""Progress and analytics router — serves data for the dashboard."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from backend.app.database import get_db
from backend.app.schemas.progress import ProgressSummary, SessionSummary, SkillNode
from backend.app.services.skill_service import (
    get_mastery_summary,
    get_skill_tree,
    get_strongest_skills,
    get_weakest_skills,
)
from backend.app.services.session_service import (
    get_session_count,
    get_student_sessions,
)
from backend.app.services.student_service import get_student

router = APIRouter(prefix="/progress", tags=["Progress"])


def _build_skill_tree(skills) -> list[SkillNode]:
    """Convert flat skill list into nested tree structure."""
    nodes: dict[int, SkillNode] = {}
    roots: list[SkillNode] = []

    for s in skills:
        node = SkillNode(
            id=s.id,
            name=s.skill_name,
            mastery_score=s.mastery_score,
            parent_id=s.parent_skill_id,
        )
        nodes[s.id] = node

    for node in nodes.values():
        if node.parent_id and node.parent_id in nodes:
            nodes[node.parent_id].children.append(node)
        else:
            roots.append(node)

    return roots


@router.get("/{student_id}/skills", response_model=list[SkillNode])
async def get_skills(student_id: int, db: DBSession = Depends(get_db)):
    """Get the skill tree for a student (nested structure)."""
    student = get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    skills = get_skill_tree(db, student_id)
    return _build_skill_tree(skills)


@router.get("/{student_id}/summary", response_model=ProgressSummary)
async def get_progress_summary(
    student_id: int, db: DBSession = Depends(get_db)
):
    """Get a progress summary for the dashboard."""
    student = get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    mastery = get_mastery_summary(db, student_id)
    sessions = get_student_sessions(db, student_id)
    total = get_session_count(db, student_id)
    strongest = get_strongest_skills(db, student_id, limit=1)
    weakest = get_weakest_skills(db, student_id, limit=1)

    topics_studied = list({s.topic for s in sessions})
    mastery_data = [{"name": k, "score": v} for k, v in mastery.items()]
    avg_mastery = sum(mastery.values()) / max(len(mastery), 1)

    return ProgressSummary(
        total_sessions=total,
        topics_studied=topics_studied,
        overall_mastery=round(avg_mastery, 1),
        strongest_skill=strongest[0].skill_name if strongest else "N/A",
        weakest_skill=weakest[0].skill_name if weakest else "N/A",
        mastery_data=mastery_data,
    )


@router.get("/{student_id}/sessions", response_model=list[SessionSummary])
async def get_sessions(
    student_id: int,
    limit: int = 20,
    db: DBSession = Depends(get_db),
):
    """Get recent session history for a student."""
    student = get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    return get_student_sessions(db, student_id, limit=limit)
