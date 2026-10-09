"""Evaluator node — checks the student's answer for correctness.

Uses the ``evaluate_math_answer`` tool for mathematical expressions and
falls back to LLM-based evaluation for free-form text answers.  Updates
the mastery score accordingly.
"""

from __future__ import annotations

import json
import os

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage

from backend.app.agents.state import ALCState
from backend.app.agents.tools.math_evaluator import evaluate_math_answer
from backend.app.llm import get_llm
from backend.app.utils.content import extract_text

# Mastery score deltas
_CORRECT_DELTA = 5
_INCORRECT_DELTA = -2


def _try_math_eval(student_answer: str, correct_answer: str) -> dict | None:
    """Attempt symbolic math evaluation; return parsed result or None."""
    try:
        raw = evaluate_math_answer.invoke(
            {"student_answer": student_answer, "correct_answer": correct_answer}
        )
        data = json.loads(raw)
        if "Could not parse" in data.get("explanation", ""):
            return None
        return data
    except Exception:  # noqa: BLE001
        return None


def _llm_eval(
    student_answer: str,
    correct_answer: str,
    question: str,
    topic: str,
    llm: BaseChatModel | None = None,
) -> dict:
    """Use the LLM to evaluate a free-form (non-math) answer."""
    prompt = f"""You are an answer evaluator for an adaptive learning system.

## Question
{question}

## Expected Answer
{correct_answer}

## Student's Answer
{student_answer}

## Topic
{topic}

Evaluate the student's answer.  Respond ONLY with valid JSON:
{{
  "correct": true/false,
  "explanation": "Brief explanation of why the answer is correct or incorrect"
}}
"""
    active_llm = llm if llm is not None else get_llm("evaluator")
    response = active_llm.invoke([SystemMessage(content=prompt)])

    # Parse the LLM's JSON response
    content = extract_text(response.content)

    try:
        # Strip markdown fences if present
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = "\n".join(cleaned.split("\n")[1:])
        if cleaned.endswith("```"):
            cleaned = "\n".join(cleaned.split("\n")[:-1])
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        # Fallback: assume incorrect if we can't parse
        return {
            "correct": False,
            "explanation": f"Could not parse evaluation. Raw response: {content[:200]}",
        }


def node_evaluate(state: ALCState, llm: BaseChatModel | None = None) -> dict:
    """Evaluate the student's submitted answer.

    Tries symbolic math evaluation first, then falls back to LLM-based
    evaluation.  Updates mastery score and returns evaluation metadata.

    Returns:
        Dict with ``is_answer_correct``, ``evaluation_feedback``,
        ``correct_answer``, and updated ``skill_scores``.
    """
    student_answer = state.get("student_answer")
    correct_answer = state.get("correct_answer")
    question_posed = state.get("question_posed")
    topic = state.get("current_topic", "General")
    skill_scores = dict(state.get("skill_scores", {}))

    # Nothing to evaluate
    if not student_answer:
        return {
            "is_answer_correct": None,
            "evaluation_feedback": "No student answer to evaluate.",
        }

    # ── Try math evaluation first ─────────────────────────────────────
    result: dict | None = None
    if correct_answer:
        result = _try_math_eval(student_answer, correct_answer)

    # ── Fall back to LLM evaluation ───────────────────────────────────
    if result is None or "correct" not in result:
        result = _llm_eval(
            student_answer=student_answer,
            correct_answer=correct_answer or "N/A",
            question=question_posed or "N/A",
            topic=topic,
            llm=llm,
        )

    is_correct = bool(result.get("correct", False))
    feedback = result.get("explanation", "")

    # ── Update mastery score ──────────────────────────────────────────
    current_mastery = skill_scores.get(topic, 0.0)
    if is_correct:
        new_mastery = min(100.0, current_mastery + _CORRECT_DELTA)
    else:
        new_mastery = max(0.0, current_mastery + _INCORRECT_DELTA)
    skill_scores[topic] = round(new_mastery, 1)

    status = "✅ Correct" if is_correct else "❌ Incorrect"
    print(
        f"📝 [EVALUATOR] {status} | "
        f"{topic} mastery: {current_mastery} → {new_mastery}"
    )

    return {
        "is_answer_correct": is_correct,
        "evaluation_feedback": feedback,
        "correct_answer": correct_answer,
        "skill_scores": skill_scores,
    }
