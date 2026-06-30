"""LangGraph orchestrator — builds and compiles the LearnMate AI graph.

Phase 3 flow (updated from Phase 2):
```
START → diagnostician → curriculum → [conditional on next_step]:
    tool_calls  → ToolNode → curriculum (loop)
    quiz        → question_generator → tutor → memory_saver → END
    evaluate    → evaluator → tutor → memory_saver → END
    reflect     → reflection → memory_saver → END
    recommend   → recommend → memory_saver → END   ← NEW in Phase 3
    explain     → tutor → memory_saver → END  (default)
```

Phase 3 changes:
- `diagnostician` node now uses ``make_diagnostician(db_session)`` factory
  so it receives the DB session for RAG memory retrieval.
- Added ``recommend`` node (Tavily resource search).
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from backend.app.agents.nodes.curriculum import node_curriculum
from backend.app.agents.nodes.diagnostician import make_diagnostician
from backend.app.agents.nodes.evaluator import node_evaluate
from backend.app.agents.nodes.memory_saver import make_memory_saver
from backend.app.agents.nodes.question_generator import node_generate_question
from backend.app.agents.nodes.recommend import node_recommend
from backend.app.agents.nodes.reflection import node_reflect
from backend.app.agents.nodes.tutor import node_tutor
from backend.app.agents.state import ALCState
from backend.app.agents.tools.curriculum_fetcher import fetch_curriculum_standard
from backend.app.agents.tools.python_repl import execute_python_code

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

load_dotenv(override=True)


# ── Tools available to the Curriculum Manager ────────────────────────────

_tools_list = [execute_python_code, fetch_curriculum_standard]


# ── Routing logic ────────────────────────────────────────────────────────

def _should_continue_after_curriculum(state: ALCState) -> str:
    """Decide where to go after the Curriculum Manager node.

    If the last message contains tool calls, route to the ``tools`` node
    so LangGraph's ``ToolNode`` can execute them.  Otherwise, route based
    on the ``next_step`` field set by the curriculum node.
    """
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    next_step = state.get("next_step", "explain")

    if next_step == "quiz":
        return "question_generator"
    elif next_step == "evaluate":
        return "evaluator"
    elif next_step == "reflect":
        return "reflection"
    elif next_step == "recommend":
        return "recommend"
    else:
        # Default: "explain" or any unknown value → tutor
        return "tutor"


# ── Graph factory ────────────────────────────────────────────────────────

def create_graph(db_session=None) -> "CompiledStateGraph":
    """Build, wire, and compile the LearnMate AI state graph.

    Args:
        db_session: Optional SQLAlchemy session for the memory saver and
                    the diagnostician RAG retrieval.
                    Pass ``None`` to skip persistence (dev / tests).

    Returns:
        A compiled LangGraph ``StateGraph`` ready for ``.invoke()`` or
        ``.stream()``.
    """
    builder = StateGraph(ALCState)

    # ── Register nodes ────────────────────────────────────────────────
    # Phase 3: diagnostician is now a factory — inject DB session for RAG
    builder.add_node("diagnostician", make_diagnostician(db_session))
    builder.add_node("curriculum", node_curriculum)
    builder.add_node("tools", ToolNode(_tools_list))
    builder.add_node("tutor", node_tutor)
    builder.add_node("evaluator", node_evaluate)
    builder.add_node("question_generator", node_generate_question)
    builder.add_node("reflection", node_reflect)
    builder.add_node("recommend", node_recommend)          # NEW Phase 3
    builder.add_node("memory_saver", make_memory_saver(db_session))

    # ── Wire edges ────────────────────────────────────────────────────
    #
    #   START → diagnostician → curriculum
    builder.add_edge(START, "diagnostician")
    builder.add_edge("diagnostician", "curriculum")

    #   curriculum → [conditional]:
    #       has tool_calls → tools → curriculum (loop back)
    #       quiz           → question_generator → tutor → memory_saver → END
    #       evaluate       → evaluator → tutor → memory_saver → END
    #       reflect        → reflection → memory_saver → END
    #       recommend      → recommend → memory_saver → END
    #       explain        → tutor → memory_saver → END
    builder.add_conditional_edges(
        "curriculum",
        _should_continue_after_curriculum,
        {
            "tools": "tools",
            "tutor": "tutor",
            "question_generator": "question_generator",
            "evaluator": "evaluator",
            "reflection": "reflection",
            "recommend": "recommend",
        },
    )

    # Tool results loop back to curriculum for verification
    builder.add_edge("tools", "curriculum")

    # Question generator → tutor (present the question to the student)
    builder.add_edge("question_generator", "tutor")

    # Evaluator → tutor (present the feedback to the student)
    builder.add_edge("evaluator", "tutor")

    # Tutor → memory_saver → END (always persist after tutoring)
    builder.add_edge("tutor", "memory_saver")
    builder.add_edge("memory_saver", END)

    # Reflection → memory_saver → END (persist reflection results)
    builder.add_edge("reflection", "memory_saver")

    # Recommend → memory_saver → END (persist session after recommendations)
    builder.add_edge("recommend", "memory_saver")

    return builder.compile()


# ── Module-level convenience ─────────────────────────────────────────────

_cached_graph: "CompiledStateGraph | None" = None


def get_graph(db_session=None) -> "CompiledStateGraph":
    """Return a (optionally cached) compiled graph instance.

    When ``db_session`` is ``None`` the graph is compiled once and
    cached.  When a session is provided a fresh graph is always built
    so that each request gets its own DB session.
    """
    global _cached_graph  # noqa: PLW0603

    if db_session is not None:
        # Per-request graph with a live DB session — never cache.
        return create_graph(db_session)

    if _cached_graph is None:
        _cached_graph = create_graph()
    return _cached_graph
