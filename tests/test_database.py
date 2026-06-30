"""V1: Database & Models — verify tables, seeding, and CRUD."""
import pytest

from backend.app.database import Base
from backend.app.models.student import Student
from backend.app.models.skill import Skill
from backend.app.models.session import Session as SessionModel
from backend.app.models.memory import Memory
from backend.app.models.seed import seed_math_skills


class TestTableCreation:
    """init_db() should create all four tables."""

    def test_tables_exist(self, db):
        tables = set(Base.metadata.tables.keys())
        assert "students" in tables
        assert "skills" in tables
        assert "sessions" in tables
        assert "memories" in tables


class TestStudentModel:
    def test_create_student(self, db):
        s = Student(name="Alice", email="alice@test.com")
        db.add(s)
        db.commit()
        db.refresh(s)
        assert s.id is not None
        assert s.name == "Alice"
        assert s.email == "alice@test.com"
        assert s.created_at is not None

    def test_student_without_email(self, db):
        s = Student(name="Bob")
        db.add(s)
        db.commit()
        assert s.email is None


class TestSeedMathSkills:
    def test_seed_creates_19_skills(self, db):
        """The math tree has 1 root + 4 branches + 14 leaves = 19 nodes."""
        s = Student(name="Seed Test")
        db.add(s)
        db.flush()
        root = seed_math_skills(db, s.id)

        all_skills = db.query(Skill).filter(Skill.student_id == s.id).all()
        assert len(all_skills) == 19

    def test_root_node_is_mathematics(self, db):
        s = Student(name="Root Test")
        db.add(s)
        db.flush()
        root = seed_math_skills(db, s.id)
        assert root.skill_name == "Mathematics"
        assert root.parent_skill_id is None

    def test_all_scores_start_at_zero(self, db):
        s = Student(name="Score Test")
        db.add(s)
        db.flush()
        seed_math_skills(db, s.id)
        skills = db.query(Skill).filter(Skill.student_id == s.id).all()
        assert all(sk.mastery_score == 0.0 for sk in skills)

    def test_branches_are_correct(self, db):
        s = Student(name="Branch Test")
        db.add(s)
        db.flush()
        root = seed_math_skills(db, s.id)
        branches = db.query(Skill).filter(
            Skill.student_id == s.id, Skill.parent_skill_id == root.id
        ).all()
        branch_names = sorted([b.skill_name for b in branches])
        assert branch_names == ["Algebra", "Calculus", "Statistics", "Trigonometry"]


class TestSessionModel:
    def test_create_session(self, db):
        s = Student(name="SessionStudent")
        db.add(s)
        db.commit()
        sess = SessionModel(student_id=s.id, topic="Algebra")
        db.add(sess)
        db.commit()
        db.refresh(sess)
        assert sess.id is not None
        assert sess.topic == "Algebra"
        assert sess.started_at is not None
        assert sess.ended_at is None


class TestMemoryModel:
    def test_create_memory(self, db):
        s = Student(name="MemoryStudent")
        db.add(s)
        db.commit()
        m = Memory(student_id=s.id, memory_type="preference", content="visual learner")
        db.add(m)
        db.commit()
        db.refresh(m)
        assert m.id is not None
        assert m.memory_type == "preference"
        assert m.content == "visual learner"
