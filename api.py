import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage

# Import your existing core components
from main_brain import graph
# 1. IMPORT THE STATE CLASS
from schema import ALCState

app = FastAPI(
    title="ALC Adaptive Tutor API",
    description="A Cognitive Agent API that diagnoses, plans, and teaches.",
    version="1.0"
)

# --- DATA MODELS ---
class ChatRequest(BaseModel):
    user_id: str
    message: str
    reset: bool = False

class ChatResponse(BaseModel):
    response: str
    current_topic: str
    current_difficulty: str
    learning_style: str

# --- SESSION STORE ---
sessions = {}

def get_session_data(user_id: str) -> dict:
    if user_id not in sessions:
        sessions[user_id] = {
            "messages": [],
            "current_topic": "General",
            "detected_learning_style": "unknown",
            "latest_diagnosis": None
        }
    return sessions[user_id]

# --- THE ENDPOINT ---
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    user_id = request.user_id
    user_input = request.message

    # Handle Reset
    if request.reset:
        if user_id in sessions:
            del sessions[user_id]
        return ChatResponse(
            response="Memory cleared.", 
            current_topic="General", 
            current_difficulty="novice", 
            learning_style="unknown"
        )

    # 1. Retrieve raw session data
    session_data = get_session_data(user_id)
    history = session_data["messages"]
    
    # 2. Append User Message
    history.append(HumanMessage(content=user_input))
    
    # 3. CONSTRUCT STATE EXPLICITLY
    # This ensures we don't miss any required keys defined in schema.py
    graph_input: ALCState = {
        "messages": history,
        "current_topic": session_data["current_topic"],
        "detected_learning_style": session_data["detected_learning_style"],
        "latest_diagnosis": session_data["latest_diagnosis"],
        # Default values for fields the brain will decide
        "current_difficulty": "intermediate", 
        "next_step": "explain"
    }
    
    try:
        # 4. Invoke the Brain
        final_state = graph.invoke(graph_input)
        
        # 5. EXTRACT OUTPUT (ROBUST FIX)
        ai_messages = final_state["messages"]
        
        # Search backwards for the last valid text response
        last_response_text = "I'm having trouble thinking right now." # Default fallback
        
        for msg in reversed(ai_messages):
            # We look for an AI Message that has content and NO tool calls
            if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
                if isinstance(msg.content, list):
                    last_response_text = "\n".join(
                        block.get("text", "") for block in msg.content if isinstance(block, dict) and "text" in block
                    )
                else:
                    last_response_text = msg.content
                break
        
        # 6. Update Session Store
        sessions[user_id]["messages"] = ai_messages
        sessions[user_id]["current_topic"] = final_state.get("current_topic", "General")
        sessions[user_id]["detected_learning_style"] = final_state.get("detected_learning_style", "unknown")
        sessions[user_id]["latest_diagnosis"] = final_state.get("latest_diagnosis")
        
        return ChatResponse(
            response=last_response_text,
            current_topic=sessions[user_id]["current_topic"],
            current_difficulty=final_state.get("current_difficulty", "intermediate"),
            learning_style=sessions[user_id]["detected_learning_style"]
        )
        
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)