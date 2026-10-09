"""Tests for LLM Factory and role-to-configuration mapping."""

import pytest
from langchain_google_genai import ChatGoogleGenerativeAI

from backend.app.llm import ROLE_CONFIG, get_llm


class TestLLMFactory:
    """Validate role configuration and get_llm factory instantiation."""

    @pytest.mark.parametrize(
        ("role", "expected_temp"),
        [
            ("diagnostician", 0.7),
            ("evaluator", 0.3),
            ("tutor", 0.7),
            ("question_generator", 0.8),
            ("curriculum", 0.7),
            ("reflection", 0.5),
        ],
    )
    def test_role_temperatures(self, role: str, expected_temp: float):
        llm = get_llm(role)
        assert isinstance(llm, ChatGoogleGenerativeAI)
        assert llm.temperature == expected_temp

    def test_unknown_role_fallback(self):
        llm = get_llm("nonexistent_role")
        assert isinstance(llm, ChatGoogleGenerativeAI)
        assert llm.temperature == 0.7

    def test_override_kwargs(self):
        llm = get_llm("evaluator", temperature=0.0)
        assert isinstance(llm, ChatGoogleGenerativeAI)
        assert llm.temperature == 0.0

    def test_all_expected_roles_present_in_config(self):
        expected_roles = {
            "diagnostician",
            "evaluator",
            "tutor",
            "question_generator",
            "curriculum",
            "reflection",
        }
        assert expected_roles.issubset(set(ROLE_CONFIG.keys()))
