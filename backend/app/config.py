from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./learnmate.db"

    # ── Vector Store ──────────────────────────────────────────────────────
    CHROMA_PATH: str = "./chroma_db"

    # ── LLM / API keys ───────────────────────────────────────────────────
    GOOGLE_API_KEY: str
    TAVILY_API_KEY: str | None = None
    LLM_MODEL: str = "gemini-2.0-flash"
    LLM_TEMPERATURE: float = 0.7

    # ── CORS ──────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # ── Debug ─────────────────────────────────────────────────────────────
    DEBUG: bool = True

    # ── LangSmith Tracing ────────────────────────────────────────────────
    # These are read directly by langchain/langsmith via env vars.
    # Declaring them here for documentation and .env validation.
    LANGSMITH_TRACING: str | None = None
    LANGSMITH_API_KEY: str | None = None
    LANGSMITH_PROJECT: str | None = None
    LANGSMITH_ENDPOINT: str | None = None


settings = Settings()  # type: ignore[call-arg]
