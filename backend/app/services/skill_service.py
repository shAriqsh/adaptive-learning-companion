"""Service layer for skill-tree and mastery operations."""

from sqlalchemy.orm import Session

from backend.app.models.skill import Skill


def get_skill_tree(db: Session, student_id: int) -> list[Skill]:
    """Return all skills for a student (flat list — caller builds the tree).

    Args:
        db: SQLAlchemy database session.
        student_id: Owner of the skill tree.

    Returns:
        All Skill rows belonging to the student.
    """
    return (
        db.query(Skill)
        .filter(Skill.student_id == student_id)
        .order_by(Skill.id)
        .all()
    )


def get_skill_by_name(db: Session, student_id: int, skill_name: str) -> Skill | None:
    """Look up a single skill by its display name.

    Args:
        db: SQLAlchemy database session.
        student_id: Owner of the skill tree.
        skill_name: Case-sensitive skill name to match.

    Returns:
        The Skill if found, otherwise None.
    """
    return (
        db.query(Skill)
        .filter(Skill.student_id == student_id, Skill.skill_name == skill_name)
        .first()
    )


def update_mastery(
    db: Session, student_id: int, skill_name: str, new_score: float
) -> Skill | None:
    """Set mastery for a skill, clamping to [0, 100].

    Args:
        db: SQLAlchemy database session.
        student_id: Owner of the skill tree.
        skill_name: Name of the skill to update.
        new_score: Raw score — will be clamped to 0–100.

    Returns:
        The updated Skill, or None if the skill was not found.
    """
    skill = get_skill_by_name(db, student_id, skill_name)
    if skill is None:
        return None

    skill.mastery_score = max(0.0, min(100.0, new_score))
    db.commit()
    db.refresh(skill)
    return skill


def get_mastery_summary(db: Session, student_id: int) -> dict[str, float]:
    """Return a flat ``{skill_name: score}`` mapping for every skill.

    Useful for serializing into chart-friendly data on the frontend.
    """
    skills = get_skill_tree(db, student_id)
    return {skill.skill_name: skill.mastery_score for skill in skills}


def get_weakest_skills(db: Session, student_id: int, limit: int = 3) -> list[Skill]:
    """Return the *limit* skills with the lowest mastery scores."""
    return (
        db.query(Skill)
        .filter(Skill.student_id == student_id)
        .order_by(Skill.mastery_score.asc())
        .limit(limit)
        .all()
    )


def get_strongest_skills(db: Session, student_id: int, limit: int = 3) -> list[Skill]:
    """Return the *limit* skills with the highest mastery scores."""
    return (
        db.query(Skill)
        .filter(Skill.student_id == student_id)
        .order_by(Skill.mastery_score.desc())
        .limit(limit)
        .all()
    )


def check_prerequisites(
    db: Session,
    student_id: int,
    skill_name: str,
    threshold: float = 40.0,
) -> bool:
    """Check whether a student meets the prerequisites for a skill.

    A skill's prerequisite is its parent in the adjacency-list tree.
    If the skill has no parent (i.e., it is a root or branch node) the
    prerequisite is considered met automatically.

    Args:
        db: SQLAlchemy database session.
        student_id: Owner of the skill tree.
        skill_name: The skill to check prerequisites for.
        threshold: Minimum mastery score required on the parent skill.
                   Defaults to 40.0 (out of 100).

    Returns:
        ``True`` if the student meets the prerequisite, ``False`` otherwise.
    """
    skill = get_skill_by_name(db, student_id, skill_name)
    if skill is None:
        return False

    # No parent → no prerequisite required
    if skill.parent_skill_id is None:
        return True

    parent = db.get(Skill, skill.parent_skill_id)
    if parent is None:
        return True  # Dangling FK — treat as met

    return float(parent.mastery_score) >= threshold


def get_next_recommended_skill(
    db: Session,
    student_id: int,
    threshold: float = 40.0,
) -> str | None:
    """Return the name of the next skill the student should work on.

    Strategy:
    1. Collect all leaf skills (skills with no children).
    2. Filter to those whose prerequisites are met (parent mastery ≥ threshold).
    3. Return the one with the lowest mastery score (most room to grow).
    4. Fall back to the globally weakest skill if no eligible leaf is found.

    Args:
        db: SQLAlchemy database session.
        student_id: Owner of the skill tree.
        threshold: Prerequisite mastery threshold (default 40.0).

    Returns:
        The skill name string, or ``None`` if the student has no skills.
    """
    all_skills = get_skill_tree(db, student_id)
    if not all_skills:
        return None

    # Build a set of IDs that appear as a parent_skill_id (i.e. branch nodes)
    parent_ids = {s.parent_skill_id for s in all_skills if s.parent_skill_id is not None}
    leaf_skills = [s for s in all_skills if s.id not in parent_ids]

    # Among leaves, find those whose prerequisites are met
    eligible = [
        s for s in leaf_skills
        if check_prerequisites(db, student_id, s.skill_name, threshold)
    ]

    if eligible:
        # Return the one with the lowest mastery (most room to improve)
        return min(eligible, key=lambda s: s.mastery_score).skill_name

    # Fallback: return globally weakest skill regardless of prerequisites
    weakest = min(all_skills, key=lambda s: s.mastery_score)
    return weakest.skill_name

