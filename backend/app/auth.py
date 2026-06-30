"""Simplified mock authentication — in-memory token store.

This is a lightweight auth layer suitable for development and demos.
Tokens are UUID strings stored in an in-memory dict; they are lost on
server restart.  No passwords are required — a student "logs in" by
providing their name.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from backend.app.database import get_db
from backend.app.services.student_service import (
    create_student,
    get_or_create_student,
)

# ── In-memory token store ────────────────────────────────────────────────
# Maps token (str) → student_id (int)
_tokens: dict[str, int] = {}


def create_token(student_id: int) -> str:
    """Generate a new session token for a student."""
    token = uuid.uuid4().hex
    _tokens[token] = student_id
    return token


def validate_token(token: str) -> int | None:
    """Return the student_id for a valid token, or None."""
    return _tokens.get(token)


def revoke_token(token: str) -> bool:
    """Revoke a token.  Returns True if it existed."""
    return _tokens.pop(token, None) is not None


# ── FastAPI dependencies ─────────────────────────────────────────────────

def _extract_token(authorization: str | None = Header(None)) -> str | None:
    """Extract Bearer token from Authorization header."""
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


async def get_current_student_id(
    authorization: str | None = Header(None),
) -> int:
    """Require a valid token and return the student_id.

    Raises 401 if the token is missing or invalid.
    """
    token = _extract_token(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    student_id = validate_token(token)
    if student_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return student_id


async def get_optional_student_id(
    authorization: str | None = Header(None),
) -> int | None:
    """Return student_id if a valid token is present, otherwise None.

    This allows routes to work both with and without auth,
    maintaining backward compatibility with existing tests.
    """
    token = _extract_token(authorization)
    if not token:
        return None
    return validate_token(token)
