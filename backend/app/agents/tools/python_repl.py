"""Python REPL tool — sandboxed code execution for math/science.

Migrated from the root-level ``tools.py``.  Pre-loads sympy, numpy, and
math so the LLM can solve and verify problems without extra imports.

NOTE: On Windows ``signal.alarm`` is unavailable.  For production,
consider using ``subprocess`` with a timeout, Docker containers, or a
dedicated sandbox service (e.g. E2B, Modal).
"""

from __future__ import annotations

import contextlib
import io
import traceback

from langchain_core.tools import tool


@tool
def execute_python_code(code: str) -> str:
    """Execute a Python snippet in a sandboxed environment.

    Use this to:
    - Solve complex math (using ``sympy`` or ``numpy``).
    - Verify answers before showing them to the user.
    - Generate data sequences for practice problems.

    IMPORTANT: The code **must** ``print()`` the final result to stdout.

    Args:
        code: A valid Python script.  ``sympy``, ``numpy``, and ``math``
              are pre-imported in the execution namespace.

    Returns:
        The captured stdout output, or an error traceback.
    """
    stdout_capture = io.StringIO()

    # Restrict builtins to a safe subset — blocks open(), exec(), eval()
    # at the top level, though a determined user could still escape.
    import builtins as _builtins

    _safe_builtins = {
        name: getattr(_builtins, name)
        for name in (
            "__import__",
            "abs", "all", "any", "bin", "bool", "chr", "complex",
            "dict", "divmod", "enumerate", "filter", "float",
            "format", "frozenset", "getattr", "hasattr", "hash",
            "hex", "id", "int", "isinstance", "issubclass", "iter",
            "len", "list", "map", "max", "min", "next", "object",
            "oct", "ord", "pow", "print", "range", "repr",
            "reversed", "round", "set", "slice", "sorted", "str",
            "sum", "tuple", "type", "zip",
        )
        if hasattr(_builtins, name)
    }

    try:
        with contextlib.redirect_stdout(stdout_capture):
            safe_globals: dict = {
                "__builtins__": _safe_builtins,
                "math": __import__("math"),
                "numpy": __import__("numpy"),
                "sympy": __import__("sympy"),
            }
            exec(code, safe_globals)  # noqa: S102

        output = stdout_capture.getvalue()
        if not output:
            return (
                "Code executed successfully but printed nothing. "
                "Did you forget 'print()'?"
            )
        return output.strip()

    except Exception:
        return f"EXECUTION ERROR:\n{traceback.format_exc()}"
