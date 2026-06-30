"""Student management router."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from backend.app.database import get_db
from backend.app.schemas.student import StudentCreate, StudentResponse
from backend.app.services.student_service import (
    create_student,
    get_student,
    list_students,
)

router = APIRouter(prefix="/students", tags=["Students"])


@router.post("", response_model=StudentResponse)
async def create_new_student(
    payload: StudentCreate, db: DBSession = Depends(get_db)
):
    """Register a new student and seed their skill tree."""
    student = create_student(db, name=payload.name, email=payload.email)
    return student


@router.get("", response_model=list[StudentResponse])
async def get_all_students(db: DBSession = Depends(get_db)):
    """List all registered students."""
    return list_students(db)


@router.get("/{student_id}", response_model=StudentResponse)
async def get_student_by_id(
    student_id: int, db: DBSession = Depends(get_db)
):
    """Retrieve a single student by ID."""
    student = get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student
