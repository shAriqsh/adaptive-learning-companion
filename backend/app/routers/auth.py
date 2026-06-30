"""Auth router — simplified mock login/logout endpoints."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session as DBSession

from backend.app.database import get_db
from backend.app.auth import (
    create_token,
    get_current_student_id,
    revoke_token,
    _extract_token,
)
from backend.app.services.student_service import (
    create_student,
    get_student,
)
from backend.app.models.student import Student

router = APIRouter(prefix="/auth", tags=["Auth"])


# ── Schemas ───────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    """Login by providing a student name.  No password required."""
    name: str
    email: str | None = None


class AuthResponse(BaseModel):
    """Returned after successful login."""
    token: str
    student: StudentInfo


class StudentInfo(BaseModel):
    """Minimal student info for auth responses."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, db: DBSession = Depends(get_db)):
    """Log in (or register) by name.  Returns a session token.

    If a student with the given name already exists, a new token is
    issued for that student.  Otherwise a new student is created.
    """
    # Look for existing student by name
    existing = db.query(Student).filter(Student.name == request.name).first()

    if existing:
        student = existing
    else:
        student = create_student(db, request.name, request.email)

    token = create_token(student.id)

    return AuthResponse(
        token=token,
        student=StudentInfo.model_validate(student),
    )


@router.get("/me", response_model=StudentInfo)
async def get_me(
    student_id: int = Depends(get_current_student_id),
    db: DBSession = Depends(get_db),
):
    """Return the currently authenticated student's info."""
    student = get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return StudentInfo.model_validate(student)


@router.post("/logout")
async def logout(authorization: str | None = Header(None)):
    """Revoke the current session token."""
    token = _extract_token(authorization)
    if token:
        revoke_token(token)
    return {"detail": "Logged out"}
