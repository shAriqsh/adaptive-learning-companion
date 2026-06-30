"""Pydantic schemas for student progress and skill trees."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SkillNode(BaseModel):
    """A single node in the hierarchical skill tree."""

    id: int
    name: str = Field(validation_alias="skill_name")
    mastery_score: float
    parent_id: int | None = Field(validation_alias="parent_skill_id")
    children: list[SkillNode] = []

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ProgressSummary(BaseModel):
    """Aggregated progress summary across all skills and sessions."""

    total_sessions: int
    topics_studied: list[str]
    overall_mastery: float  # average across all skills
    strongest_skill: str
    weakest_skill: str
    mastery_data: list[dict]  # for charts: [{name: str, score: float}]


class SessionSummary(BaseModel):
    """Summary of a single tutoring session."""

    id: int
    topic: str
    summary: str | None
    started_at: datetime
    ended_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
