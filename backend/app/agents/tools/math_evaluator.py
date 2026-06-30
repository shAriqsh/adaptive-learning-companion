"""Math answer evaluator tool.

Uses SymPy to symbolically compare a student's answer against the
expected correct answer, handling algebraic equivalence (e.g. ``x+1``
vs ``1+x``), simplification differences, and numeric approximations.
"""

from __future__ import annotations

import json

from langchain_core.tools import tool


@tool
def evaluate_math_answer(student_answer: str, correct_answer: str) -> str:
    """Evaluate whether a student's mathematical answer is correct.

    Uses SymPy to parse and simplify both expressions, then checks if
    they are symbolically equivalent.

    Args:
        student_answer: The student's answer as a math expression string.
        correct_answer: The correct answer as a math expression string.

    Returns:
        A JSON string with keys:
        - ``correct``  (bool)
        - ``student_simplified``  (str)
        - ``expected_simplified`` (str)
        - ``explanation`` (str)
    """
    import sympy  # local import keeps startup fast

    result: dict = {
        "correct": False,
        "student_simplified": "",
        "expected_simplified": "",
        "explanation": "",
    }

    # ── Parse student answer ──────────────────────────────────────────
    try:
        student_expr = sympy.sympify(student_answer)
        result["student_simplified"] = str(sympy.simplify(student_expr))
    except (sympy.SympifyError, TypeError, ValueError) as exc:
        result["explanation"] = (
            f"Could not parse student answer '{student_answer}': {exc}"
        )
        return json.dumps(result)

    # ── Parse correct answer ──────────────────────────────────────────
    try:
        correct_expr = sympy.sympify(correct_answer)
        result["expected_simplified"] = str(sympy.simplify(correct_expr))
    except (sympy.SympifyError, TypeError, ValueError) as exc:
        result["explanation"] = (
            f"Could not parse correct answer '{correct_answer}': {exc}"
        )
        return json.dumps(result)

    # ── Symbolic comparison ───────────────────────────────────────────
    try:
        difference = sympy.simplify(student_expr - correct_expr)
        is_correct = difference == 0

        # Fallback: numeric evaluation for transcendental expressions
        if not is_correct:
            try:
                numeric_diff = abs(complex(difference))
                is_correct = numeric_diff < 1e-10
            except (TypeError, ValueError):
                pass

        result["correct"] = is_correct
        if is_correct:
            result["explanation"] = "Correct! The expressions are equivalent."
        else:
            result["explanation"] = (
                f"Incorrect. Your simplified answer is "
                f"{result['student_simplified']}, but the expected answer "
                f"simplifies to {result['expected_simplified']}."
            )
    except Exception as exc:  # noqa: BLE001
        result["explanation"] = f"Error during comparison: {exc}"

    return json.dumps(result)
