"""LLM factory and centralized configuration for LearnMate AI.

Consolidates LLM initialization, environment variable loading, and role-based
hyperparameter management (temperature, model name) in a single module.
"""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

# Load environment once for the entire application
load_dotenv(override=True)

DEFAULT_MODEL = os.getenv("LLM_MODEL", "gemini-2.0-flash")

ROLE_CONFIG: dict[str, dict[str, Any]] = {
    "diagnostician": {
        "model": DEFAULT_MODEL,
        "temperature": 0.7,
    },
    "evaluator": {
        "model": DEFAULT_MODEL,
        "temperature": 0.3,  # deterministic evaluation
    },
    "tutor": {
        "model": DEFAULT_MODEL,
        "temperature": 0.7,
    },
    "question_generator": {
        "model": DEFAULT_MODEL,
        "temperature": 0.8,  # variety and creativity
    },
    "curriculum": {
        "model": DEFAULT_MODEL,
        "temperature": 0.7,
    },
    "reflection": {
        "model": DEFAULT_MODEL,
        "temperature": 0.5,
    },
    "recommend": {
        "model": DEFAULT_MODEL,
        "temperature": 0.7,
    },
}


def get_llm(role: str = "default", **overrides: Any) -> BaseChatModel:
    """Create and return a configured ChatGoogleGenerativeAI instance for a role.

    Args:
        role: Functional role (e.g. 'diagnostician', 'evaluator', 'tutor').
        **overrides: Optional parameter overrides (e.g. temperature=0.0).

    Returns:
        A BaseChatModel instance configured for the specified role.
    """
    model_name = os.getenv("LLM_MODEL", DEFAULT_MODEL)
    default_config = {"model": model_name, "temperature": 0.7}
    config = ROLE_CONFIG.get(role, default_config).copy()
    # Always reflect runtime LLM_MODEL if not explicitly configured differently
    if "model" not in overrides and config.get("model") == DEFAULT_MODEL:
        config["model"] = model_name
    config.update(overrides)

    return ChatGoogleGenerativeAI(**config)
