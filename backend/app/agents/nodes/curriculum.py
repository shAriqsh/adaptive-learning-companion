"""Curriculum Manager node — decides the next learning step.

Receives the diagnosis and skill scores, then determines whether to
explain a concept, quiz the student, or evaluate a previous answer.
Can invoke tools (python_repl, curriculum_fetcher) to gather data.
"""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from backend.app.agents.state import ALCState
from backend.app.agents.tools.curriculum_fetcher import fetch_curriculum_standard
from backend.app.agents.tools.python_repl import execute_python_code
from backend.app.llm import get_llm

tools_list = [execute_python_code, fetch_curriculum_standard]


def node_curriculum(state: ALCState, llm: BaseChatModel | None = None) -> dict:
    """Design the next learning step based on diagnosis and skill scores.

    The Curriculum Manager acts as the orchestrator between content
    retrieval tools and the Tutor.  It decides *what* to teach and
    lets the Tutor decide *how*.

    Returns:
        Dict with updated ``messages`` and optionally ``next_step``.
    """
    diagnosis = state.get("latest_diagnosis", "No diagnosis yet.")
    topic = state.get("current_topic", "General")
    difficulty = state.get("current_difficulty", "medium")
    skill_scores = state.get("skill_scores", {})
    current_mastery = skill_scores.get(topic, 0.0)
    student_answer = state.get("student_answer")
    question_posed = state.get("question_posed")

    messages = state["messages"]
    if not messages:
        messages = [HumanMessage(content="Begin the lesson.")]

    # ── Decide next_step hint ─────────────────────────────────────────
    next_step = "explain"  # default
    if student_answer and question_posed:
        next_step = "evaluate"
    elif current_mastery >= 40:
        next_step = "quiz"

    prompt = f"""You are the Curriculum Manager for an adaptive math tutor.

## Context
- **Student Diagnosis**: {diagnosis}
- **Topic**: {topic}
- **Current Difficulty**: {difficulty}
- **Mastery Score**: {current_mastery}/100
- **Skill Scores**: {skill_scores}
- **Suggested Next Step**: {next_step}

## Your Responsibilities
1. If you need to generate or verify a specific math problem, call ``execute_python_code`` to solve it first.
2. If you need syllabus or prerequisite information, call ``fetch_curriculum_standard``.
3. Once you have all the data, provide clear **instructions for the Tutor** — what concept to cover, what example to use, or what question to pose.
4. If a student answer is pending evaluation, instruct the Tutor accordingly.

## Output
Write natural-language instructions that the Tutor node will use to craft its response to the student.  Include any computed answers or curriculum data you retrieved.

Do NOT speak directly to the student — you are talking to the Tutor.
"""

    active_llm = llm if llm is not None else get_llm("curriculum")
    try:
        active_llm = active_llm.bind_tools(tools_list)
    except (NotImplementedError, AttributeError):
        pass

    response = active_llm.invoke(
        [SystemMessage(content=prompt)] + messages
    )

    return {
        "messages": [response],
        "next_step": next_step,
    }
