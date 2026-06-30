"""Resource search tool — Tavily web search for educational content.

Falls back to curated mock data when ``TAVILY_API_KEY`` is not set, so
the agent pipeline always functions in development.
"""

from __future__ import annotations

import json
import os

from langchain_core.tools import tool


# ── Mock data for offline / keyless development ──────────────────────────

_MOCK_RESOURCES: dict[str, list[dict[str, str]]] = {
    "default": [
        {
            "title": "Khan Academy — Math Courses",
            "url": "https://www.khanacademy.org/math",
            "type": "course",
            "description": "Free, world-class math courses from arithmetic to calculus.",
        },
        {
            "title": "3Blue1Brown — Essence of Calculus",
            "url": "https://www.youtube.com/playlist?list=PLZHQObOWTQDMsr9K-rj53DwVRMYO3t5Yr",
            "type": "video",
            "description": "Visual, intuitive explanations of calculus concepts.",
        },
        {
            "title": "Paul's Online Math Notes",
            "url": "https://tutorial.math.lamar.edu/",
            "type": "article",
            "description": "Comprehensive notes and practice problems for algebra through differential equations.",
        },
        {
            "title": "Brilliant.org — Math Practice",
            "url": "https://brilliant.org/courses/#math-foundational",
            "type": "practice",
            "description": "Interactive problem sets that build intuition.",
        },
    ],
}


def _get_mock_results(query: str, topic: str) -> str:
    """Return curated placeholder resources."""
    resources = _MOCK_RESOURCES.get(topic.lower(), _MOCK_RESOURCES["default"])
    return json.dumps(
        {
            "source": "mock",
            "note": "TAVILY_API_KEY not set — returning placeholder resources.",
            "query": query,
            "topic": topic,
            "results": resources,
        },
        indent=2,
    )


@tool
def search_learning_resources(query: str, topic: str) -> str:
    """Search for educational resources on a math topic.

    Returns relevant videos, articles, and practice sets.  Uses the
    Tavily search API when available, otherwise falls back to curated
    placeholder resources.

    Args:
        query: The specific concept the student needs help with.
        topic: The broader math topic area (e.g. ``"calculus"``).

    Returns:
        A JSON string listing matched resources with title, URL, type,
        and description.
    """
    api_key = os.getenv("TAVILY_API_KEY")

    if not api_key:
        return _get_mock_results(query, topic)

    # ── Live Tavily search ────────────────────────────────────────────
    try:
        from tavily import TavilyClient  # type: ignore[import-untyped]

        client = TavilyClient(api_key=api_key)
        search_query = f"{query} {topic} math tutorial educational"

        response = client.search(
            query=search_query,
            search_depth="basic",
            max_results=5,
            include_answer=False,
        )

        results = [
            {
                "title": r.get("title", "Untitled"),
                "url": r.get("url", ""),
                "type": "article",
                "description": r.get("content", "")[:200],
            }
            for r in response.get("results", [])
        ]

        return json.dumps(
            {
                "source": "tavily",
                "query": query,
                "topic": topic,
                "results": results,
            },
            indent=2,
        )

    except ImportError:
        return json.dumps(
            {
                "source": "error",
                "error": "tavily-python package is not installed. Run: uv add tavily-python",
                "fallback": json.loads(_get_mock_results(query, topic)),
            },
            indent=2,
        )
    except Exception as exc:  # noqa: BLE001
        return json.dumps(
            {
                "source": "error",
                "error": f"Tavily search failed: {exc}",
                "fallback": json.loads(_get_mock_results(query, topic)),
            },
            indent=2,
        )
