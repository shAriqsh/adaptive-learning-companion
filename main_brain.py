import os
from IPython.display import Image, display
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from schema import ALCState, TopicMastery # Import your schema
from langgraph.prebuilt import ToolNode
from profile_store import update_profile, load_profile
from tools import execute_python_code, fetch_curriculum_standard
from dotenv import load_dotenv
load_dotenv(override=True)

# Config
llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite-preview", temperature=0.7) 
tools_list = [execute_python_code, fetch_curriculum_standard]
curriculum_llm = llm.bind_tools(tools_list)

# --- NODE 1: THE DIAGNOSTICIAN ---
def node_diagnose(state: ALCState):
    # LOAD MEMORY HERE
    user_profile = load_profile("student_01")
    
    # Extract context
    topic = state.get("current_topic", "General")
    known_style = user_profile["preferences"]["learning_style"]
    current_mastery = user_profile["mastery_map"].get(topic, {}).get("competency", 0.0)
    
    history = state["messages"][-3:] 
    
    prompt = f"""
    Analyze the student.
    Context:
    - User Learning Style: {known_style}
    - Current Mastery Score: {current_mastery}/1.0
    
    Output structured diagnosis (Is the user correct? What is the misconception?).
    """
    
    analysis = llm.invoke([SystemMessage(content=prompt)] + history)
    
    # Robustly extract text content if it's a list of blocks
    content_text = analysis.content
    if isinstance(analysis.content, list):
        # Join all text parts if it's a list of content blocks
        content_text = "\n".join(
            block.get("text", "") for block in analysis.content if isinstance(block, dict) and "text" in block
        )
    
    print(f"🕵️ [DIAGNOSIS]: {content_text}")
    
    return {
        "latest_diagnosis": content_text,
        # We assume the analysis might contain clues about style
        "detected_learning_style": "visual" if "visual" in content_text.lower() else known_style
    }

# --- NODE 2: THE CURRICULUM MANAGER ---
def node_curriculum(state: ALCState):
    diagnosis = state.get("latest_diagnosis", "No diagnosis yet")
    topic = state.get("current_topic", "General")
    messages = state["messages"]

    if not messages:
        messages = [HumanMessage(content="Begin the lesson.")]
    
    prompt = f"""
    You are the Curriculum Manager.
    User Diagnosis: {diagnosis}
    Topic: {topic}
    
    Your goal: Design the NEXT learning step.
    
    DECISION LOGIC:
    1. If you need to generate a specific math problem, call 'execute_python_code' to solve it first.
    2. If you are unsure of the syllabus, call 'fetch_curriculum_standard'.
    3. If you have all data, simply provide instructions for the Tutor.
    4. If you need to call a tool, call it with the appropriate arguments.
    """
    
    response = curriculum_llm.invoke([SystemMessage(content=prompt)] + messages)
    
    return {"messages": [response]}

# --- NODE 3: THE INSTRUCTIONAL DESIGNER (The Speaker) ---
def node_tutor(state: ALCState):
    prompt = f"""
    You are the ALC Tutor (The Interface).
    Your colleague (Curriculum Manager) has prepared the lesson content.
    
    If you see a Math Result in the history, present it as a practice problem.
    Do NOT mention 'running python'. Just act like you created the problem.
    Use Socratic style.
    Ask probing questions to check understanding.
    Break down complex concepts into simpler steps.
    Keep your responses concise and conversational.
    If the user makes a mistake, ask them to re-evaluate their specific error (don't just say "wrong").
    If the user asks a question, ask a probing question back to check their understanding.
    Never give the full solution immediately. Break it down into small steps.
    """
    
    response = llm.invoke([SystemMessage(content=prompt)] + state["messages"])
    return {"messages": [response]}

def should_continue(state: ALCState):
    last_message = state["messages"][-1]
    
    # If the LLM made a tool call, go to 'tools'
    if last_message.tool_calls:
        return "tools"
    # Otherwise, go to 'tutor' to speak to the user
    return "tutor"

def node_memory_saver(state: ALCState):
    """
    This node runs at the very end. 
    It doesn't generate text; it just commits side-effects to the database.
    """
    update_profile(
        user_id="student_01",
        topic=state.get("current_topic", "General"),
        diagnosis=state.get("latest_diagnosis", ""),
        style=state.get("detected_learning_style", "unknown")
    )
    # Return nothing, just pass through
    return {}
# --- GRAPH CONSTRUCTION ---
builder = StateGraph(ALCState)

builder.add_node("diagnostician", node_diagnose)
builder.add_node("curriculum", node_curriculum)
builder.add_node("tools", ToolNode(tools_list)) # Prebuilt node executes the Python code
builder.add_node("tutor", node_tutor)
builder.add_node("saver", node_memory_saver)

# Edges
builder.add_edge(START, "diagnostician")
builder.add_edge("diagnostician", "curriculum")

# The Fork in the Road
builder.add_conditional_edges(
    "curriculum",
    should_continue,
    {
        "tools": "tools",
        "tutor": "tutor"
    }
)

# If tools run, go back to Curriculum to verify the result
builder.add_edge("tools", "curriculum") 
builder.add_edge("tutor", "saver") 
builder.add_edge("saver", END)     

graph = builder.compile()

# --- SIMULATION ---
# if __name__ == "__main__":
#     print("🚀 ALC System Online with STEM Capabilities...")
    
#     # Simulation: User wants a quadratic equation problem
#     initial_state = {
#         "messages": [HumanMessage(content="Teach me about slope.")],
#         "current_topic": "Algebra",
#         "current_difficulty": "intermediate",
#         "detected_learning_style": "code-first",
#         "latest_diagnosis": "User is ready for practice."
#     }
#     # png= graph.get_graph().draw_mermaid_png()
#     # display(Image(png))
#     # print(graph.get_graph().draw_ascii())
    
# events = graph.stream(initial_state)

# for event in events:
#     for node, data in event.items():
#         print(f"---- NODE: {node.upper()} ----")
#         if data is None:
#             continue
#         if "messages" in data:
#             last_msg = data["messages"][-1]
#             # If it's a tool call, print what it wants to do
#             if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
#                 print(f"🛠️  CALLING TOOL: {last_msg.tool_calls[0]['name']}")
#                 print(f"    ARGS: {last_msg.tool_calls[0]['args']}")
#             # If it's a tool output (result)
#             elif hasattr(last_msg, 'content') and "ToolMessage" in str(type(last_msg)): 
#                 print(f"📊 TOOL RESULT: {last_msg.content}")
#             else:
#                 print(f"💬 MSG: {last_msg.content[:100]}...")
