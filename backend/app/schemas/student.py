"""Pydantic schemas for student CRUD operations."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StudentCreate(BaseModel):
    """Payload for creating a new student."""

    name: str
    email: str | None = None


class StudentResponse(BaseModel):
    """Serialized student returned from the API."""

    id: int
    name: str
    email: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
