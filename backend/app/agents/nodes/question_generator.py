"""Question Generator node — creates adaptive practice questions.

Selects difficulty based on the student's current mastery score,
accounts for their learning style, and generates both the question
and its correct answer.
"""

from __future__ import annotations

import json
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from backend.app.agents.state import ALCState
from backend.app.llm import get_llm
from backend.app.utils.content import extract_text


def _select_difficulty(mastery: float) -> str:
    """Choose question difficulty based on mastery score (0-100)."""
    if mastery < 40:
        return "easy"
    if mastery < 70:
        return "medium"
    return "hard"


def _gather_previous_mistakes(messages: list, limit: int = 5) -> str:
    """Extract recent mistake patterns from conversation history."""
    mistakes: list[str] = []
    for msg in messages[-20:]:
        content = msg.content if hasattr(msg, "content") else str(msg)
        if isinstance(content, list):
            content = " ".join(
                b.get("text", "") for b in content if isinstance(b, dict)
            )
        content_lower = content.lower()
        if any(kw in content_lower for kw in ("incorrect", "wrong", "mistake", "error", "❌")):
            mistakes.append(content[:150])
            if len(mistakes) >= limit:
                break
    return "\n".join(mistakes) if mistakes else "No recent mistakes recorded."


def node_generate_question(state: ALCState, llm: BaseChatModel | None = None) -> dict:
    """Generate an adaptive practice question for the student.

    Difficulty scales with mastery.  The prompt asks for both the
    question text and the correct answer so downstream evaluation
    can be automated.

    Returns:
        Dict with ``question_posed``, ``correct_answer``,
        ``current_difficulty``, and an AI ``messages`` entry
        presenting the question to the student.
    """
    topic = state.get("current_topic", "General")
    skill_scores = state.get("skill_scores", {})
    mastery = skill_scores.get(topic, 0.0)
    style = state.get("detected_learning_style", "unknown")
    messages = state.get("messages", [])

    difficulty = _select_difficulty(mastery)
    mistakes = _gather_previous_mistakes(messages)

    prompt = f"""You are a math question generator for an adaptive learning system.

## Parameters
- **Topic**: {topic}
- **Difficulty**: {difficulty}
- **Student's Learning Style**: {style}
- **Current Mastery**: {mastery}/100

## Previous Mistakes to Avoid Repeating
{mistakes}

## Instructions
Generate ONE practice question.  Respond ONLY with valid JSON:

{{
  "question": "The full question text, clearly stated. If the style is 'visual', include a diagram or table in the question.",
  "correct_answer": "The correct answer as a mathematical expression or short text.",
  "hint": "A brief hint that guides without giving away the answer."
}}

Guidelines:
- **easy**: Simple, single-step problems.  Directly test one concept.
- **medium**: Multi-step problems.  Require combining 2 concepts.
- **hard**: Complex problems requiring deeper reasoning or multiple techniques.
- Tailor the question framing to the student's learning style.
- Do NOT reuse the exact same mistakes the student made before — test the concept differently.

Respond ONLY with the JSON object — no markdown fences, no extra text.
"""

    active_llm = llm if llm is not None else get_llm("question_generator")
    response = active_llm.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content="Generate the practice question now."),
    ])

    content = extract_text(response.content)

    # Parse structured response
    try:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = "\n".join(cleaned.split("\n")[1:])
        if cleaned.endswith("```"):
            cleaned = "\n".join(cleaned.split("\n")[:-1])
        data = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        # Fallback: use the raw text as the question
        data = {
            "question": content or f"Solve a {difficulty} {topic} problem.",
            "correct_answer": "",
            "hint": "",
        }

    question_text = data.get("question", "")
    correct_answer = data.get("correct_answer", "")
    hint = data.get("hint", "")

    # Build student-facing message
    student_msg = f"📝 **Practice Question** ({difficulty.title()})\n\n{question_text}"
    if hint:
        student_msg += f"\n\n💡 *Hint: {hint}*"

    print(
        f"❓ [QUESTION] Difficulty={difficulty} | "
        f"Topic={topic} | Mastery={mastery}"
    )

    return {
        "question_posed": question_text,
        "correct_answer": correct_answer,
        "current_difficulty": difficulty,
        "student_answer": None,  # reset for next round
        "is_answer_correct": None,  # reset
        "evaluation_feedback": None,  # reset
        "messages": [AIMessage(content=student_msg)],
    }
