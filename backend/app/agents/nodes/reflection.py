"""Reflection node — end-of-session analysis.

Runs at the end of a session to summarise what was learned, identify
topics that need more practice, and produce a concise session summary.
"""

from __future__ import annotations

import json
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from backend.app.agents.state import ALCState
from backend.app.llm import get_llm
from backend.app.utils.content import extract_text


def node_reflect(state: ALCState, llm: BaseChatModel | None = None) -> dict:
    """Analyse the full conversation and produce session reflections.

    Uses the LLM to identify what was learned, what needs practice,
    and write a human-readable session summary.

    Returns:
        Dict with ``session_summary``, ``topics_learned``, and
        ``topics_need_practice``.
    """
    topic = state.get("current_topic", "General")
    skill_scores = state.get("skill_scores", {})
    messages = state.get("messages", [])

    # Build a condensed conversation transcript for the LLM
    transcript_lines: list[str] = []
    for msg in messages:
        role = getattr(msg, "type", "unknown")
        content = msg.content if hasattr(msg, "content") else str(msg)
        if isinstance(content, list):
            content = " ".join(
                b.get("text", "") for b in content if isinstance(b, dict)
            )
        # Truncate very long messages
        if len(content) > 300:
            content = content[:300] + "…"
        transcript_lines.append(f"[{role}]: {content}")

    transcript = "\n".join(transcript_lines[-20:])  # last 20 messages max

    prompt = f"""You are a Session Reflection Analyst for an adaptive math tutor.

## Session Info
- Main Topic: {topic}
- Skill Scores at End: {json.dumps(skill_scores)}

## Conversation Transcript (most recent)
{transcript}

## Your Task
Analyse the session and produce a JSON object with exactly these keys:

{{
  "session_summary": "A 2-3 sentence summary of what happened in this session.",
  "topics_learned": ["list", "of", "topics the student demonstrated understanding of"],
  "topics_need_practice": ["list", "of", "topics where the student struggled or made errors"]
}}

Respond ONLY with the JSON object — no markdown fences, no extra text.
"""

    active_llm = llm if llm is not None else get_llm("reflection")
    response = active_llm.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content="Analyse the session and produce the JSON summary."),
    ])

    content = extract_text(response.content)

    # Parse the structured response
    try:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = "\n".join(cleaned.split("\n")[1:])
        if cleaned.endswith("```"):
            cleaned = "\n".join(cleaned.split("\n")[:-1])
        data = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        # Graceful fallback
        data = {
            "session_summary": content[:500] if content else "Session completed.",
            "topics_learned": [topic],
            "topics_need_practice": [],
        }

    print(f"🪞 [REFLECTION] {data.get('session_summary', '')[:100]}...")

    return {
        "session_summary": data.get("session_summary", ""),
        "topics_learned": data.get("topics_learned", []),
        "topics_need_practice": data.get("topics_need_practice", []),
    }
