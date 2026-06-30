"""V4: Agent Tools — verify Python REPL, math evaluator, curriculum fetcher."""
import json
import pytest


class TestPythonRepl:
    def test_simple_print(self):
        from backend.app.agents.tools.python_repl import execute_python_code
        result = execute_python_code.invoke({"code": "print(2 + 2)"})
        assert "4" in result

    def test_sympy_derivative(self):
        from backend.app.agents.tools.python_repl import execute_python_code
        code = "from sympy import symbols, diff; x = symbols('x'); print(diff(x**2, x))"
        result = execute_python_code.invoke({"code": code})
        assert "2*x" in result

    def test_invalid_code_returns_error(self):
        from backend.app.agents.tools.python_repl import execute_python_code
        result = execute_python_code.invoke({"code": "raise ValueError('boom')"})
        assert "ERROR" in result or "ValueError" in result

    def test_no_output_message(self):
        from backend.app.agents.tools.python_repl import execute_python_code
        result = execute_python_code.invoke({"code": "x = 42"})
        assert "print" in result.lower() or "nothing" in result.lower()


class TestMathEvaluator:
    def test_correct_answer(self):
        from backend.app.agents.tools.math_evaluator import evaluate_math_answer
        result = json.loads(evaluate_math_answer.invoke({
            "student_answer": "2*x",
            "correct_answer": "2*x",
        }))
        assert result["correct"] is True

    def test_equivalent_forms(self):
        from backend.app.agents.tools.math_evaluator import evaluate_math_answer
        result = json.loads(evaluate_math_answer.invoke({
            "student_answer": "x + x",
            "correct_answer": "2*x",
        }))
        assert result["correct"] is True

    def test_incorrect_answer(self):
        from backend.app.agents.tools.math_evaluator import evaluate_math_answer
        result = json.loads(evaluate_math_answer.invoke({
            "student_answer": "3*x",
            "correct_answer": "2*x",
        }))
        assert result["correct"] is False

    def test_parse_error_handled(self):
        from backend.app.agents.tools.math_evaluator import evaluate_math_answer
        result = json.loads(evaluate_math_answer.invoke({
            "student_answer": "not_math!!!",
            "correct_answer": "2*x",
        }))
        # Should not crash; returns a valid JSON with correct=False or error
        assert isinstance(result, dict)


class TestCurriculumFetcher:
    def test_calculus_returns_content(self):
        from backend.app.agents.tools.curriculum_fetcher import fetch_curriculum_standard
        result = fetch_curriculum_standard.invoke({"topic": "calculus"})
        assert len(result) > 0
        assert "calculus" in result.lower() or "derivative" in result.lower()

    def test_algebra_returns_content(self):
        from backend.app.agents.tools.curriculum_fetcher import fetch_curriculum_standard
        result = fetch_curriculum_standard.invoke({"topic": "algebra"})
        assert len(result) > 0

    def test_unknown_topic_returns_default(self):
        from backend.app.agents.tools.curriculum_fetcher import fetch_curriculum_standard
        result = fetch_curriculum_standard.invoke({"topic": "underwater_basket_weaving"})
        assert len(result) > 0  # should return a default/fallback
