# Adaptive Learning Companion (ALC) 🧠

The **Adaptive Learning Companion** is a cognitive agent-based tutoring system designed to provide a personalized, Socratic learning experience. Unlike traditional chatbots, ALC uses a multi-agent workflow to diagnose a student's understanding, plan a tailored curriculum, and execute lessons using interactive tools.

## 🚀 Key Features

-   **Multi-Agent Workflow:** Built with **LangGraph**, the system separates concerns into specialized nodes: Diagnostician, Curriculum Manager, and Tutor.
-   **Dynamic Diagnosis:** Real-time analysis of student misconceptions and knowledge gaps.
-   **Socratic Tutoring:** Instead of giving answers, the AI asks probing questions to lead students to their own "Aha!" moments.
-   **Integrated Tools:** Includes a Python execution sandbox for math/science problems and a curriculum standard fetcher.
-   **Long-Term Memory:** Persists student mastery scores and learning preferences across sessions in a JSON-based profile store.
-   **FastAPI Backend:** A robust API layer for integrating with frontend applications.

---

## 🏗️ Architecture & Workflow

The system follows a cyclic graph-based logic:

1.  **Diagnostician (`node_diagnose`):** Analyzes the chat history to update the "Internal Monologue" about the student's mastery level and learning style.
2.  **Curriculum Manager (`node_curriculum`):** Decisions on the next pedagogical step. It can choose to call tools (like a Python solver) or move directly to instruction.
3.  **Tool Executor (`ToolNode`):** Executes external functions (e.g., standardizing a math problem via Python).
4.  **Tutor (`node_tutor`):** The "voice" of the system. Translates the curriculum plan into conversational, Socratic dialogue.
5.  **Memory Saver (`node_memory_saver`):** At the end of every turn, it commits the latest diagnosis and mastery scores to the permanent `student_profile.json`.

---

## 📂 Project Structure

-   `api.py`: FastAPI server and session management.
-   `main_brain.py`: The core LangGraph definition and node logic.
-   `profile_store.py`: Logic for loading and saving the student's persistent profile.
-   `schema.py`: Type definitions and State definitions for the LangGraph workflow.
-   `tools.py`: Specialized tools for the AI (Python execution, Syllabus fetching).
-   `student_profile.json`: The "Long-term Memory" database for student progress.

---

## 🛠️ Setup & Installation

### 1. Prerequisites
-   Python 3.10+
-   A Google Gemini API Key (set as `GOOGLE_API_KEY` in a `.env` file)

### 2. Installation
```bash
# Install dependencies (using uv or pip)
pip install -r requirements.txt
# OR
uv sync
```

### 3. Run the API
```bash
python api.py
```
The server will start at `http://localhost:8000`.

---

## 📡 API Usage

### `POST /chat`
Interact with the tutor.

**Request Body:**
```json
{
  "user_id": "student_01",
  "message": "What is Wave-Particle Duality?",
  "reset": false
}
```

**Response:**
```json
{
  "response": "Imagine a spinning fan...",
  "current_topic": "Quantum Physics",
  "current_difficulty": "intermediate",
  "learning_style": "visual"
}
```

---

## 📊 The Student Profile
The system tracks progress in `student_profile.json`. Example entry:
```json
{
  "user_id": "student_01",
  "mastery_map": {
    "Quantum Physics": {
      "competency": 0.4,
      "mistakes": ["Macroscopic Bias"]
    }
  },
  "preferences": {
    "learning_style": "visual"
  }
}
```

## 📜 License
MIT
