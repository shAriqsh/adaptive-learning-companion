"""LearnMate AI — FastAPI application entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.database import init_db


# ── Lifespan ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks."""
    # Startup: create tables if they don't exist
    init_db()
    print("✅ Database tables ready.")

    # Report tracing status
    import os
    tracing = os.getenv("LANGSMITH_TRACING", "").lower() == "true"
    project = os.getenv("LANGSMITH_PROJECT", "default")
    if tracing:
        print(f"📊 LangSmith tracing enabled → project: {project}")
    else:
        print("📊 LangSmith tracing disabled (set LANGSMITH_TRACING=true to enable)")

    yield
    # Shutdown: nothing needed for SQLite
    print("👋 Shutting down.")


# ── App ───────────────────────────────────────────────────────────────────

app = FastAPI(
    title="LearnMate AI",
    description=(
        "An intelligent tutoring system that adapts to each student's "
        "learning journey — powered by LangGraph multi-agent orchestration."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────

from backend.app.routers.chat import router as chat_router  # noqa: E402
from backend.app.routers.students import router as students_router  # noqa: E402
from backend.app.routers.progress import router as progress_router  # noqa: E402
from backend.app.routers.auth import router as auth_router  # noqa: E402

app.include_router(chat_router, prefix="/api")
app.include_router(students_router, prefix="/api")
app.include_router(progress_router, prefix="/api")
app.include_router(auth_router, prefix="/api")


# ── Health Check ──────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "service": "LearnMate AI"}


# ── Dev Server ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
