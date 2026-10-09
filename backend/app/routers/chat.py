"""Chat router — thin HTTP adapter delegating to ChatOrchestrator."""
from __future__ import annotations

try:
    from langsmith import traceable
except ImportError:
    def traceable(**kwargs):
        def decorator(fn):
            return fn
        return decorator

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from backend.app.database import get_db
from backend.app.orchestrator import ChatOrchestrator
from backend.app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["Chat"])
orchestrator = ChatOrchestrator()
# Backward-compatibility alias for tests referencing active thread mapping
_active_threads = orchestrator._active_threads


@router.post("", response_model=ChatResponse)
@traceable(name="chat_endpoint", run_type="chain")
def chat(request: ChatRequest, db: DBSession = Depends(get_db)) -> ChatResponse:
    """Send a message to the AI tutor and receive a response."""
    return orchestrator.handle(request, db)
