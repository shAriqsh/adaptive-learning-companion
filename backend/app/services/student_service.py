"""Service layer for student CRUD operations."""

from sqlalchemy.orm import Session

from backend.app.models.student import Student
from backend.app.models.seed import seed_math_skills


def create_student(db: Session, name: str, email: str | None = None) -> Student:
    """Create a new student and seed their initial math skill tree.

    Args:
        db: SQLAlchemy database session.
        name: Display name for the student.
        email: Optional email address.

    Returns:
        The newly created Student ORM instance.
    """
    student = Student(name=name, email=email)
    db.add(student)
    db.flush()  # populate student.id before seeding skills
    seed_math_skills(db, student.id)
    db.commit()
    db.refresh(student)
    return student


def get_student(db: Session, student_id: int) -> Student | None:
    """Fetch a student by primary key.

    Returns:
        The Student if found, otherwise None.
    """
    return db.query(Student).filter(Student.id == student_id).first()


def get_or_create_student(db: Session, student_id: int) -> Student:
    """Return the student with the given id, creating a default one if missing.

    This is useful for first-contact scenarios where the frontend sends an id
    that may not exist in the database yet.

    Args:
        db: SQLAlchemy database session.
        student_id: The id to look up.

    Returns:
        An existing or newly created Student.
    """
    student = get_student(db, student_id)
    if student is not None:
        return student
    return create_student(db, name=f"Student {student_id}")


def list_students(db: Session) -> list[Student]:
    """Return all students ordered by creation date (newest first)."""
    return db.query(Student).order_by(Student.created_at.desc()).all()
