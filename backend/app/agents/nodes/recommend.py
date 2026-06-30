"""Recommend node — surfaces educational resources using Tavily or mock data.

Triggered when ``next_step == "recommend"``.  Calls the
``search_learning_resources`` tool and stores the results in
``recommended_resources`` in the graph state.
"""

from __future__ import annotations

import json
import logging

from backend.app.agents.state import ALCState

logger = logging.getLogger(__name__)


def node_recommend(state: ALCState) -> dict:
    """Search for learning resources relevant to the student's current topic.

    Args:
        state: Current graph state.

    Returns:
        Dict with ``recommended_resources`` (list of formatted strings) and
        a new AI message presenting the resources to the student.
    """
    from langchain_core.messages import AIMessage

    topic = state.get("current_topic", "General")
    diagnosis = state.get("latest_diagnosis", "") or ""
    difficulty = state.get("current_difficulty", "easy")

    # Build a targeted query from the diagnosis or just use the topic
    if diagnosis:
        # Extract a short phrase from diagnosis to sharpen the query
        query = f"{topic} {difficulty} level tutorial"
    else:
        query = f"{topic} math tutorial for beginners"

    logger.info("📚 [RECOMMEND] Searching resources for topic=%s", topic)

    resources: list[str] = []
    resource_text = ""

    try:
        from backend.app.agents.tools.resource_search import search_learning_resources

        raw = search_learning_resources.invoke({"query": query, "topic": topic})  # type: ignore[arg-type]
        data = json.loads(raw) if isinstance(raw, str) else raw

        results = data.get("results", [])
        for r in results:
            title = r.get("title", "Resource")
            url = r.get("url", "")
            description = r.get("description", "")
            resource_str = f"**{title}** — {description} ({url})"
            resources.append(resource_str)

        if resources:
            formatted_list = "\n".join(f"- {r}" for r in resources)
            resource_text = (
                f"Here are some great resources for **{topic}**:\n\n"
                f"{formatted_list}\n\n"
                "Pick whichever format works best for you. Let me know when you're ready to continue!"
            )
        else:
            resource_text = (
                f"I couldn't find specific resources right now, but for **{topic}** "
                "I'd suggest checking Khan Academy or 3Blue1Brown on YouTube — both are excellent!"
            )

    except Exception:
        logger.warning("📚 [RECOMMEND] Resource search failed.", exc_info=True)
        resource_text = (
            f"I had trouble searching for resources right now. "
            f"For **{topic}**, Khan Academy and Paul's Online Math Notes are great starting points."
        )

    logger.info("📚 [RECOMMEND] Found %d resources for student.", len(resources))

    return {
        "recommended_resources": resources,
        "messages": [AIMessage(content=resource_text)],
    }
