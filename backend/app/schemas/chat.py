"""Pydantic schemas for the chat API."""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Incoming chat message from a student."""

    student_id: int
    message: str
    topic: str | None = None  # optional topic override
    reset: bool = False


class ChatResponse(BaseModel):
    """Response returned after processing a chat message."""

    response: str
    current_topic: str
    current_difficulty: str
    learning_style: str
    mastery_score: float | None = None
    session_id: int | None = None
    recommended_resources: list[dict] | None = None
