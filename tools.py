import io
import sys
import contextlib
import traceback
from langchain_core.tools import tool

# 1. THE STEM ENGINE (Python REPL)
@tool
def execute_python_code(code: str) -> str:
    """
    A Python shell. Use this to execute python commands.
    Input should be a valid python script.
    Use this to:
    - Solve complex math (using 'sympy' or 'numpy').
    - Verify answers before showing them to the user.
    - Generate data sequences for practice problems.
    
    IMPORTANT: The code must print the final result to stdout.
    """
    # Create a buffer to capture the print() output
    stdout_capture = io.StringIO()
    
    try:
        # Redirect stdout to our buffer
        with contextlib.redirect_stdout(stdout_capture):
            # Define a safe global context with math libraries pre-loaded
            safe_globals = {
                "math": __import__("math"),
                "numpy": __import__("numpy"),
                "sympy": __import__("sympy"),
            }
            # Execute the code
            exec(code, safe_globals)
            
        # Get the output
        output = stdout_capture.getvalue()
        if not output:
            return "Code executed successfully but printed nothing. Did you forget 'print()'?"
        return output.strip()

    except Exception as e:
        return f"EXECUTION ERROR: {traceback.format_exc()}"

# 2. THE KNOWLEDGE RETRIEVER (Mock MCP for Khan/Wolfram)
@tool
def fetch_curriculum_standard(topic: str) -> str:
    """
    Simulates fetching syllabus data from an LMS or Khan Academy via MCP.
    Use this to ensure the generated problem aligns with 10th-grade standards.
    """
    # In a real app, this would be: client.get("https://api.khanacademy.org/...")
    
    knowledge_base = {
        "calculus": "Standard: Derivatives of polynomials. Avoid chain rule for now.",
        "algebra": "Standard: Quadratic equations using factorization. No complex roots.",
        "physics": "Standard: Newtonian mechanics (F=ma). Frictionless surfaces only."
    }
    
    for key, value in knowledge_base.items():
        if key in topic.lower():
            return value
            
    return "Standard: General introduction. Keep difficulty low."