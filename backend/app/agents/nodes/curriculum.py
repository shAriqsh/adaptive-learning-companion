"""Curriculum Manager node — decides the next learning step.

Receives the diagnosis and skill scores, then determines whether to
explain a concept, quiz the student, or evaluate a previous answer.
Can invoke tools (python_repl, curriculum_fetcher) to gather data.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from backend.app.agents.state import ALCState
from backend.app.agents.tools.curriculum_fetcher import fetch_curriculum_standard
from backend.app.agents.tools.python_repl import execute_python_code

load_dotenv(override=True)

llm = ChatGoogleGenerativeAI(
    model=os.getenv("LLM_MODEL", "gemini-2.0-flash"),
    temperature=0.7,
)

# Bind tools so the LLM can request tool calls
tools_list = [execute_python_code, fetch_curriculum_standard]
curriculum_llm = llm.bind_tools(tools_list)


def node_curriculum(state: ALCState) -> dict:
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

    response = curriculum_llm.invoke(
        [SystemMessage(content=prompt)] + messages
    )

    return {
        "messages": [response],
        "next_step": next_step,
    }
