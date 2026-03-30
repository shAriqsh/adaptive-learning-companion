from typing import List, Dict, Literal, Optional, Annotated
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

# 1. The Mastery Profile (Long-Term structured memory)
class TopicMastery(TypedDict):
    topic_id: str
    competency_score: float  # 0.0 to 1.0
    common_errors: List[str] # e.g., ["sign_error", "conceptual_misunderstanding"]
    successful_strategies: List[str] # e.g., ["visual_analogy", "code_example"]

# 2. The Current Session State (Short-Term context)
class ALCState(TypedDict):
    # Chat History
    messages: Annotated[list, add_messages]
    
    # The Active Subject
    current_topic: str
    current_difficulty: Literal["novice", "intermediate", "advanced"]
    
    # Diagnosis: The AI's internal monologue about the user
    latest_diagnosis: Optional[str] # e.g., "User confused velocity with acceleration"
    detected_learning_style: Literal["visual", "textual", "socratic", "code-first", "unknown"]
    
    # The Plan: What the AI intends to do next
    next_step: Literal["explain", "quiz", "diagram", "tool_call"]