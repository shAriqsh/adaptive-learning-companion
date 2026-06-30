from __future__ import annotations

from sqlalchemy.orm import Session as DBSession

from backend.app.models.skill import Skill


# ── Mathematics skill-tree blueprint ──────────────────────────────────────
#
# Mathematics (root)
# ├── Algebra
# │   ├── Linear Equations
# │   ├── Quadratic Equations
# │   ├── Functions
# │   └── Polynomials
# ├── Calculus
# │   ├── Limits
# │   ├── Derivatives
# │   ├── Integrals
# │   └── Chain Rule
# ├── Trigonometry
# │   ├── Trigonometric Functions
# │   ├── Trigonometric Identities
# │   └── Inverse Trigonometric Functions
# └── Statistics
#     ├── Mean Median Mode
#     ├── Probability
#     └── Standard Deviation

MATH_TREE: dict[str, list[str]] = {
    "Algebra": [
        "Linear Equations",
        "Quadratic Equations",
        "Functions",
        "Polynomials",
    ],
    "Calculus": [
        "Limits",
        "Derivatives",
        "Integrals",
        "Chain Rule",
    ],
    "Trigonometry": [
        "Trigonometric Functions",
        "Trigonometric Identities",
        "Inverse Trigonometric Functions",
    ],
    "Statistics": [
        "Mean Median Mode",
        "Probability",
        "Standard Deviation",
    ],
}


def seed_math_skills(db: DBSession, student_id: int) -> Skill:
    """Populate the full Mathematics skill tree for a student.

    All skills are created with ``mastery_score = 0.0``.

    Parameters
    ----------
    db:
        An active SQLAlchemy session.
    student_id:
        The id of the student who owns this tree.

    Returns
    -------
    Skill
        The root *Mathematics* skill (fully flushed with an ``id``).
    """
    # Root node
    root = Skill(
        student_id=student_id,
        skill_name="Mathematics",
        parent_skill_id=None,
        mastery_score=0.0,
    )
    db.add(root)
    db.flush()  # assigns root.id

    for branch_name, leaves in MATH_TREE.items():
        branch = Skill(
            student_id=student_id,
            skill_name=branch_name,
            parent_skill_id=root.id,
            mastery_score=0.0,
        )
        db.add(branch)
        db.flush()  # assigns branch.id

        for leaf_name in leaves:
            leaf = Skill(
                student_id=student_id,
                skill_name=leaf_name,
                parent_skill_id=branch.id,
                mastery_score=0.0,
            )
            db.add(leaf)

    db.commit()
    db.refresh(root)
    return root
