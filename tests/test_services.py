"""V2: Services — verify business logic in student, skill, session, memory services."""
import pytest

from backend.app.models.student import Student
from backend.app.models.skill import Skill
from backend.app.models.session import Session as SessionModel
from backend.app.models.memory import Memory
from backend.app.models.seed import seed_math_skills

from backend.app.services.student_service import (
    create_student,
    get_student,
    get_or_create_student,
    list_students,
)
from backend.app.services.skill_service import (
    get_skill_tree,
    get_skill_by_name,
    update_mastery,
    get_mastery_summary,
    get_weakest_skills,
    get_strongest_skills,
    check_prerequisites,
    get_next_recommended_skill,
)
from backend.app.services.session_service import (
    create_session,
    get_session,
    update_session,
    get_student_sessions,
    get_session_count,
)
from backend.app.services.memory_service import (
    store_memory,
    get_memories,
    get_all_preferences,
    get_weaknesses,
)


# ── Student Service ──────────────────────────────────────────────────────

class TestStudentService:
    def test_create_student_seeds_skills(self, db):
        student = create_student(db, name="Alice", email="a@b.com")
        assert student.id is not None
        skills = db.query(Skill).filter(Skill.student_id == student.id).all()
        assert len(skills) == 19

    def test_get_student(self, db):
        student = create_student(db, name="Bob")
        fetched = get_student(db, student.id)
        assert fetched is not None
        assert fetched.name == "Bob"

    def test_get_student_returns_none(self, db):
        assert get_student(db, 9999) is None

    def test_get_or_create_existing(self, db):
        student = create_student(db, name="Carol")
        same = get_or_create_student(db, student.id)
        assert same.id == student.id

    def test_get_or_create_new(self, db):
        new = get_or_create_student(db, 9999)
        assert new is not None
        assert new.name.startswith("Student")

    def test_list_students(self, db):
        create_student(db, name="D1")
        create_student(db, name="D2")
        students = list_students(db)
        assert len(students) >= 2


# ── Skill Service ────────────────────────────────────────────────────────

class TestSkillService:
    def _make_student(self, db):
        return create_student(db, name="SkillTest")

    def test_get_skill_tree(self, db):
        s = self._make_student(db)
        tree = get_skill_tree(db, s.id)
        assert len(tree) == 19

    def test_get_skill_by_name(self, db):
        s = self._make_student(db)
        skill = get_skill_by_name(db, s.id, "Limits")
        assert skill is not None
        assert skill.skill_name == "Limits"

    def test_get_skill_by_name_missing(self, db):
        s = self._make_student(db)
        assert get_skill_by_name(db, s.id, "Nonexistent") is None

    def test_update_mastery(self, db):
        s = self._make_student(db)
        updated = update_mastery(db, s.id, "Limits", 75.5)
        assert updated is not None
        assert updated.mastery_score == 75.5

    def test_update_mastery_clamps_high(self, db):
        s = self._make_student(db)
        updated = update_mastery(db, s.id, "Limits", 150.0)
        assert updated.mastery_score == 100.0

    def test_update_mastery_clamps_low(self, db):
        s = self._make_student(db)
        updated = update_mastery(db, s.id, "Limits", -20.0)
        assert updated.mastery_score == 0.0

    def test_get_mastery_summary(self, db):
        s = self._make_student(db)
        summary = get_mastery_summary(db, s.id)
        assert isinstance(summary, dict)
        assert "Mathematics" in summary
        assert "Limits" in summary
        assert len(summary) == 19

    def test_weakest_and_strongest(self, db):
        s = self._make_student(db)
        update_mastery(db, s.id, "Limits", 80.0)
        update_mastery(db, s.id, "Derivatives", 10.0)
        weakest = get_weakest_skills(db, s.id, limit=1)
        strongest = get_strongest_skills(db, s.id, limit=1)
        # Strongest should be Limits (80), weakest should be one of the 0.0 skills
        assert strongest[0].mastery_score >= weakest[0].mastery_score


# ── Session Service ──────────────────────────────────────────────────────

class TestSessionService:
    def test_create_and_get_session(self, db):
        s = create_student(db, name="SessTest")
        sess = create_session(db, s.id, "Calculus")
        assert sess.id is not None
        assert sess.topic == "Calculus"
        fetched = get_session(db, sess.id)
        assert fetched is not None
        assert fetched.topic == "Calculus"

    def test_update_session(self, db):
        s = create_student(db, name="UpdTest")
        sess = create_session(db, s.id, "Algebra")
        update_session(db, sess.id, summary="Covered equations")
        db.refresh(sess)
        assert sess.summary == "Covered equations"

    def test_get_student_sessions(self, db):
        s = create_student(db, name="ListTest")
        create_session(db, s.id, "Algebra")
        create_session(db, s.id, "Calculus")
        sessions = get_student_sessions(db, s.id)
        assert len(sessions) == 2

    def test_session_count(self, db):
        s = create_student(db, name="CountTest")
        create_session(db, s.id, "T1")
        create_session(db, s.id, "T2")
        create_session(db, s.id, "T3")
        assert get_session_count(db, s.id) == 3


# ── Memory Service ───────────────────────────────────────────────────────

class TestMemoryService:
    def test_store_and_retrieve(self, db):
        s = create_student(db, name="MemTest")
        store_memory(db, s.id, "preference", "visual learner")
        mems = get_memories(db, s.id)
        assert len(mems) >= 1
        assert mems[0].content == "visual learner"

    def test_filter_by_type(self, db):
        s = create_student(db, name="FilterTest")
        store_memory(db, s.id, "preference", "likes diagrams")
        store_memory(db, s.id, "weakness", "struggles with limits")
        prefs = get_all_preferences(db, s.id)
        weaks = get_weaknesses(db, s.id)
        assert all(m.memory_type == "preference" for m in prefs)
        assert all(m.memory_type == "weakness" for m in weaks)


# ── Skill Prerequisite Service ───────────────────────────────────────────

class TestSkillPrerequisites:
    """Tests for prerequisite checking and next-skill recommendation."""

    def test_check_prerequisites_root_node(self, db):
        """Root skill (no parent) always meets prerequisites."""
        from backend.app.services.student_service import create_student
        student = create_student(db, name="PreqTest1")
        # "Mathematics" is the root with no parent
        result = check_prerequisites(db, student.id, "Mathematics")
        assert result is True

    def test_check_prerequisites_branch_no_parent_check(self, db):
        """Branch skill (Algebra) has Mathematics as parent at mastery=0 → not met at threshold=40."""
        from backend.app.services.student_service import create_student
        student = create_student(db, name="PreqTest2")
        # All skills start at 0 — parent mastery is 0, threshold default is 40
        result = check_prerequisites(db, student.id, "Linear Equations", threshold=40.0)
        assert result is False

    def test_check_prerequisites_met_when_parent_mastered(self, db):
        """Prerequisite is met when parent mastery >= threshold."""
        from backend.app.services.student_service import create_student
        student = create_student(db, name="PreqTest3")
        # Bring Algebra mastery up to 50
        update_mastery(db, student.id, "Algebra", 50.0)
        result = check_prerequisites(db, student.id, "Linear Equations", threshold=40.0)
        assert result is True

    def test_check_prerequisites_unknown_skill_returns_false(self, db):
        """check_prerequisites returns False for a skill that doesn't exist."""
        from backend.app.services.student_service import create_student
        student = create_student(db, name="PreqTest4")
        result = check_prerequisites(db, student.id, "Quantum Mechanics", threshold=40.0)
        assert result is False

    def test_get_next_recommended_skill_returns_string(self, db):
        """get_next_recommended_skill should return a skill name string."""
        from backend.app.services.student_service import create_student
        student = create_student(db, name="RecommTest1")
        result = get_next_recommended_skill(db, student.id)
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_next_recommended_skill_prefers_eligible_leaves(self, db):
        """When prerequisites are met for some leaf, it is preferred over ineligible leaves."""
        from backend.app.services.student_service import create_student
        student = create_student(db, name="RecommTest2")
        # Bring Statistics mastery up so its leaves become eligible
        update_mastery(db, student.id, "Statistics", 50.0)
        result = get_next_recommended_skill(db, student.id)
        # Should be one of the Statistics leaves (all at 0 mastery, prerequisites now met)
        stats_leaves = {"Mean Median Mode", "Probability", "Standard Deviation"}
        assert result in stats_leaves
