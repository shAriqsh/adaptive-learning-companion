"""Tutor node — the student-facing conversationalist.

Adapts its explanation style to the detected learning style, uses
Socratic questioning, and provides encouraging feedback when evaluation
results are available.
"""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage

from backend.app.agents.state import ALCState
from backend.app.llm import get_llm


# ── Style-specific prompt fragments ─────────────────────────────────────

_STYLE_PROMPTS: dict[str, str] = {
    "visual": (
        "The student learns best VISUALLY.\n"
        "- Use diagrams, ASCII art, and step-by-step visual breakdowns.\n"
        "- Show graphs or tables where applicable.\n"
        "- Use formatting (bullet points, numbered lists) to structure information spatially.\n"
        "- When explaining equations, align terms vertically to show transformations."
    ),
    "analogical": (
        "The student learns best through ANALOGIES.\n"
        "- Use real-world examples and metaphors to explain abstract concepts.\n"
        "- Relate math concepts to everyday situations (e.g., slope as steepness of a hill).\n"
        "- Compare new topics to ones the student already knows.\n"
        "- Tell mini-stories to illustrate why a concept works."
    ),
    "procedural": (
        "The student learns best through STEP-BY-STEP PROCEDURES.\n"
        "- Use numbered instructions for every method.\n"
        "- Present algorithms clearly: Step 1, Step 2, Step 3…\n"
        "- Emphasise *when* to apply each rule.\n"
        "- Provide checklists the student can follow for similar problems."
    ),
    "unknown": (
        "The student's learning style is not yet determined.\n"
        "- Use a balanced mix of visual, analogical, and procedural approaches.\n"
        "- Pay attention to which style the student responds best to."
    ),
}


def node_tutor(state: ALCState, llm: BaseChatModel | None = None) -> dict:
    """Generate the student-facing tutoring response.

    Takes the Curriculum Manager's instructions (in the latest messages),
    the diagnosis, and the evaluation feedback to craft an engaging,
    style-adapted explanation or follow-up question.

    Returns:
        Dict with updated ``messages``.
    """
    style = state.get("detected_learning_style", "unknown")
    topic = state.get("current_topic", "General")
    difficulty = state.get("current_difficulty", "medium")
    is_correct = state.get("is_answer_correct")
    eval_feedback = state.get("evaluation_feedback")
    question_posed = state.get("question_posed")
    retrieved_memories = state.get("retrieved_memories", [])

    # ── Build style guidance ──────────────────────────────────────────
    style_guidance = _STYLE_PROMPTS.get(style, _STYLE_PROMPTS["unknown"])

    # ── Build memory context section ──────────────────────────────────
    memory_section = ""
    if retrieved_memories:
        formatted = "\n".join(f"  - {m}" for m in retrieved_memories)
        memory_section = (
            "\n## What We Know About This Student (Long-Term Memory)\n"
            f"{formatted}\n"
            "Use this to personalise your teaching — address known weaknesses,\n"
            "build on strengths, and match the student's learning preferences.\n"
        )

    # ── Build feedback section ────────────────────────────────────────
    feedback_section = ""
    if question_posed and is_correct is not None:
        if is_correct:
            feedback_section = (
                "\n## Recent Evaluation\n"
                f"The student answered the question correctly! ✅\n"
                f"Feedback: {eval_feedback or 'Great job!'}\n"
                "Celebrate their success briefly, then move on to the next concept or a harder question."
            )
        else:
            feedback_section = (
                "\n## Recent Evaluation\n"
                f"The student's answer was incorrect. ❌\n"
                f"Feedback: {eval_feedback or 'Lets look at this again.'}\n"
                "Do NOT give the full correct answer immediately. Instead:\n"
                "1. Point out where their reasoning went wrong.\n"
                "2. Ask a guiding question to nudge them toward the right approach.\n"
                "3. Encourage them to try again."
            )

    prompt = f"""You are the LearnMate AI Tutor — the student-facing interface.

## Style Adaptation
{style_guidance}

## Topic & Difficulty
- Topic: {topic}
- Difficulty: {difficulty}
{memory_section}{feedback_section}

## Core Teaching Principles
1. **Socratic Method**: Ask probing questions — don't just lecture.
2. **Concise & Engaging**: Keep responses focused. No walls of text.
3. **Encouraging Tone**: Be supportive. Celebrate progress.
4. **Never Reveal Full Solutions Immediately**: Break problems into small steps.
5. **If the student asks a question**, respond with a guiding question back.
6. **If you see a Math Result from a tool**, present it as a practice problem — never mention "running code" or "Python".

Your colleague (the Curriculum Manager) has left instructions in the recent messages. Follow them to craft your response to the student.
"""

    active_llm = llm if llm is not None else get_llm("tutor")
    response = active_llm.invoke(
        [SystemMessage(content=prompt)] + state["messages"]
    )

    return {"messages": [response]}
