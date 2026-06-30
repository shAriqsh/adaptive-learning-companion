"""Curriculum knowledge-base fetcher tool.

Expanded from the original 3-entry ``tools.py`` to cover every topic in
the LearnMate AI skill tree.  Each entry provides a structured overview
that the Curriculum Manager node can use to plan lessons.
"""

from __future__ import annotations

from langchain_core.tools import tool

# ── Knowledge Base ────────────────────────────────────────────────────────

KNOWLEDGE_BASE: dict[str, dict[str, str | list[str]]] = {
    # ── Algebra ───────────────────────────────────────────────────────
    "linear equations": {
        "description": (
            "Equations of the form ax + b = c.  Covers single-variable "
            "linear equations and systems of two linear equations."
        ),
        "prerequisites": ["arithmetic", "order of operations"],
        "key_concepts": [
            "isolating the variable",
            "inverse operations",
            "slope-intercept form (y = mx + b)",
            "systems of equations (substitution, elimination)",
        ],
        "common_misconceptions": [
            "Forgetting to apply the same operation to both sides",
            "Confusing slope with y-intercept",
            "Sign errors when moving terms across the equals sign",
        ],
    },
    "quadratic equations": {
        "description": (
            "Equations of the form ax² + bx + c = 0.  Includes factoring, "
            "completing the square, and the quadratic formula."
        ),
        "prerequisites": ["linear equations", "exponents", "factoring"],
        "key_concepts": [
            "standard form vs vertex form",
            "factoring trinomials",
            "completing the square",
            "quadratic formula: x = (-b ± √(b²-4ac)) / 2a",
            "discriminant and nature of roots",
        ],
        "common_misconceptions": [
            "Forgetting ± in the quadratic formula",
            "Incorrectly factoring when a ≠ 1",
            "Confusing complex roots with 'no solution'",
        ],
    },
    "functions": {
        "description": (
            "The concept of a function as a mapping from input to output.  "
            "Domain, range, composition, and inverse functions."
        ),
        "prerequisites": ["linear equations", "coordinate geometry"],
        "key_concepts": [
            "definition of a function",
            "domain and range",
            "function notation f(x)",
            "composition f(g(x))",
            "inverse functions",
            "vertical line test",
        ],
        "common_misconceptions": [
            "Thinking every equation is a function",
            "Confusing f(x+1) with f(x) + 1",
            "Errors in finding inverse functions",
        ],
    },
    "polynomials": {
        "description": (
            "Expressions with multiple terms involving non-negative integer "
            "exponents.  Covers operations, factoring, and the remainder "
            "theorem."
        ),
        "prerequisites": ["arithmetic", "exponents", "linear equations"],
        "key_concepts": [
            "degree, leading coefficient, constant term",
            "adding, subtracting, multiplying polynomials",
            "polynomial long division and synthetic division",
            "factor theorem and remainder theorem",
            "zeros / roots of polynomials",
        ],
        "common_misconceptions": [
            "Confusing degree with number of terms",
            "Errors in distributing negative signs",
            "Forgetting the remainder in polynomial division",
        ],
    },
    # ── Calculus ──────────────────────────────────────────────────────
    "limits": {
        "description": (
            "The foundational concept of calculus — the value a function "
            "approaches as the input approaches a given point."
        ),
        "prerequisites": ["functions", "polynomials"],
        "key_concepts": [
            "intuitive definition of a limit",
            "one-sided limits",
            "limits at infinity",
            "limit laws (sum, product, quotient)",
            "squeeze theorem",
            "continuity and its connection to limits",
        ],
        "common_misconceptions": [
            "Believing the limit must equal the function value",
            "Confusion between limit existing and function being defined",
            "Incorrect cancellation in 0/0 indeterminate forms",
        ],
    },
    "derivatives": {
        "description": (
            "The rate of change of a function.  Covers definition, rules, "
            "and basic applications."
        ),
        "prerequisites": ["limits", "functions", "polynomials"],
        "key_concepts": [
            "definition via limits: f'(x) = lim h→0 [f(x+h)-f(x)]/h",
            "power rule, product rule, quotient rule",
            "derivatives of common functions (polynomials, trig, exp, log)",
            "tangent line and instantaneous rate of change",
            "higher-order derivatives",
        ],
        "common_misconceptions": [
            "Confusing average rate of change with instantaneous",
            "Misapplying the product rule as f'·g'",
            "Forgetting the chain rule for composite functions",
        ],
    },
    "chain rule": {
        "description": (
            "A differentiation rule for composite functions: "
            "d/dx[f(g(x))] = f'(g(x)) · g'(x)."
        ),
        "prerequisites": ["derivatives", "functions"],
        "key_concepts": [
            "identifying the outer and inner functions",
            "applying the chain rule step-by-step",
            "chain rule combined with product/quotient rule",
            "implicit differentiation using the chain rule",
        ],
        "common_misconceptions": [
            "Forgetting to multiply by the inner derivative",
            "Difficulty identifying nested compositions",
            "Confusing chain rule with product rule",
        ],
    },
    "integrals": {
        "description": (
            "The reverse of differentiation — accumulation of quantities.  "
            "Definite and indefinite integrals, and the Fundamental Theorem "
            "of Calculus."
        ),
        "prerequisites": ["derivatives", "limits"],
        "key_concepts": [
            "antiderivatives and the constant of integration",
            "definite integrals and area under a curve",
            "Fundamental Theorem of Calculus (parts I & II)",
            "basic integration rules (power rule, substitution)",
            "integration by parts",
        ],
        "common_misconceptions": [
            "Forgetting the constant of integration (+C)",
            "Confusing definite and indefinite integrals",
            "Incorrect u-substitution boundaries",
        ],
    },
    # ── Trigonometry ──────────────────────────────────────────────────
    "trig functions": {
        "description": (
            "Sine, cosine, tangent, and their reciprocals.  Covers unit "
            "circle, graphs, and right-triangle definitions."
        ),
        "prerequisites": ["functions", "coordinate geometry"],
        "key_concepts": [
            "SOH-CAH-TOA for right triangles",
            "unit circle definition",
            "graphs of sin, cos, tan (amplitude, period, phase shift)",
            "reciprocal functions: csc, sec, cot",
            "radians vs degrees",
        ],
        "common_misconceptions": [
            "Mixing up radians and degrees",
            "Forgetting the sign of trig functions in different quadrants",
            "Confusing amplitude with period",
        ],
    },
    "trig identities": {
        "description": (
            "Fundamental identities used to simplify trigonometric "
            "expressions and prove equivalences."
        ),
        "prerequisites": ["trig functions", "algebra"],
        "key_concepts": [
            "Pythagorean identities: sin²θ + cos²θ = 1",
            "double-angle formulas",
            "sum and difference formulas",
            "half-angle formulas",
            "product-to-sum and sum-to-product",
        ],
        "common_misconceptions": [
            "Incorrectly applying double-angle formulas",
            "Mixing up sum and difference formula signs",
            "Trying to 'cancel' trig functions algebraically",
        ],
    },
    "inverse trig": {
        "description": (
            "arcsin, arccos, arctan — the inverse trigonometric functions "
            "and their domains/ranges."
        ),
        "prerequisites": ["trig functions", "functions"],
        "key_concepts": [
            "definition and restricted domains",
            "arcsin, arccos, arctan ranges",
            "composing trig and inverse trig functions",
            "solving equations using inverse trig",
        ],
        "common_misconceptions": [
            "Forgetting domain restrictions (e.g. arcsin only [-1, 1])",
            "Confusing arcsin(x) with 1/sin(x)",
            "Not accounting for all solutions in an equation",
        ],
    },
    # ── Statistics & Probability ──────────────────────────────────────
    "mean median mode": {
        "description": (
            "Measures of central tendency for data sets — mean (average), "
            "median (middle value), and mode (most frequent)."
        ),
        "prerequisites": ["arithmetic"],
        "key_concepts": [
            "calculating mean, median, mode",
            "effect of outliers on mean vs median",
            "weighted mean",
            "choosing the best measure for a data set",
        ],
        "common_misconceptions": [
            "Forgetting to sort data before finding the median",
            "Confusing mean and median for skewed distributions",
            "Thinking there is always exactly one mode",
        ],
    },
    "probability": {
        "description": (
            "The mathematics of chance — theoretical, experimental, and "
            "conditional probability."
        ),
        "prerequisites": ["arithmetic", "fractions"],
        "key_concepts": [
            "sample space and events",
            "P(A) = favorable / total outcomes",
            "addition rule for mutually exclusive events",
            "multiplication rule for independent events",
            "conditional probability P(A|B)",
            "Bayes' theorem (introductory level)",
        ],
        "common_misconceptions": [
            "Confusing independent and mutually exclusive events",
            "Adding probabilities of non-mutually exclusive events without subtracting the intersection",
            "Confusing conditional probability direction: P(A|B) ≠ P(B|A)",
        ],
    },
    "standard deviation": {
        "description": (
            "A measure of spread / dispersion in a data set.  Covers "
            "variance, population vs sample standard deviation."
        ),
        "prerequisites": ["mean median mode", "arithmetic"],
        "key_concepts": [
            "variance as average of squared deviations",
            "standard deviation as √variance",
            "population (σ) vs sample (s) standard deviation",
            "interpreting standard deviation in context",
            "empirical rule (68-95-99.7)",
        ],
        "common_misconceptions": [
            "Forgetting to square the deviations",
            "Using n instead of n-1 for sample standard deviation",
            "Thinking a larger SD always means 'bad' data",
        ],
    },
}


def _format_entry(topic: str, entry: dict) -> str:
    """Format a knowledge base entry into a readable string."""
    lines = [f"📘 Topic: {topic.title()}"]
    lines.append(f"Description: {entry['description']}")
    lines.append(f"Prerequisites: {', '.join(entry['prerequisites'])}")
    lines.append(f"Key Concepts: {', '.join(entry['key_concepts'])}")
    lines.append(
        f"Common Misconceptions: {'; '.join(entry['common_misconceptions'])}"
    )
    return "\n".join(lines)


@tool
def fetch_curriculum_standard(topic: str) -> str:
    """Fetch curriculum data for a math topic.

    Returns structured information including the topic description,
    prerequisites, key concepts, and common misconceptions.  Use this
    to ensure generated problems align with proper curriculum standards.

    Args:
        topic: The math topic to look up (e.g. ``"quadratic equations"``).

    Returns:
        A formatted string with curriculum details, or a generic
        fallback if the topic is not in the knowledge base.
    """
    topic_lower = topic.lower().strip()

    # Exact match
    if topic_lower in KNOWLEDGE_BASE:
        return _format_entry(topic_lower, KNOWLEDGE_BASE[topic_lower])

    # Substring / fuzzy match
    for key, entry in KNOWLEDGE_BASE.items():
        if key in topic_lower or topic_lower in key:
            return _format_entry(key, entry)

    # List available topics so the LLM can retry
    available = ", ".join(sorted(KNOWLEDGE_BASE.keys()))
    return (
        f"Topic '{topic}' not found in curriculum database.\n"
        f"Available topics: {available}\n"
        "Standard: General introduction.  Keep difficulty low."
    )
