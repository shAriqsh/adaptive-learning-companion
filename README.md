# LearnMate AI — Adaptive Learning Companion 🎓

An **intelligent math tutoring system** powered by a multi-agent LangGraph workflow that adapts to each student's learning journey. It goes beyond a simple chatbot — diagnosing knowledge gaps through Socratic questioning, tracking mastery across a hierarchical skill tree, remembering learning preferences across sessions, and presenting progress through an interactive dashboard.

![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue?logo=python&logoColor=white)
![Next.js 16](https://img.shields.io/badge/Next.js-16-black?logo=next.js&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-green?logo=langchain&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Gemini-2.5--flash-blue?logo=google&logoColor=white)

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| **Multi-Agent Workflow** | 7 specialized LangGraph nodes — diagnostician, curriculum manager, tutor, evaluator, question generator, reflection, and memory saver |
| **Socratic Tutoring** | The AI asks probing questions instead of giving away answers, guiding students to their own insights |
| **Adaptive Difficulty** | Questions scale from easy → medium → hard based on real-time mastery scores |
| **Learning Style Detection** | Automatically detects visual, analogical, or procedural learning preferences and adapts teaching style |
| **19-Node Skill Tree** | Hierarchical math curriculum (Algebra → Calculus → Trigonometry → Statistics) with per-skill mastery tracking |
| **Dual Memory System** | Short-term memory (LangGraph checkpointer) for conversation continuity + long-term memory (ChromaDB + SQLite) for cross-session recall |
| **SymPy Math Evaluation** | Symbolic answer checking — recognizes `2*x` and `2x` as equivalent |
| **Resource Recommendations** | Tavily-powered search for relevant learning resources (videos, articles, courses) |
| **Interactive Dashboard** | Recharts radar/bar charts, React Flow skill tree visualization, session history |
| **LangSmith Tracing** | Full observability of every agent node invocation, LLM token usage, and latency |

---

## 🏗️ Architecture

### Agent Graph Flow

```
START → diagnostician → curriculum → [conditional]:
  tool_calls → ToolNode → curriculum (loop)
  quiz       → question_generator → tutor → memory_saver → END
  evaluate   → evaluator → tutor → memory_saver → END
  reflect    → reflection → memory_saver → END
  recommend  → recommend → memory_saver → END
  explain    → tutor → memory_saver → END  (default)
```

### Memory Architecture

| Layer | Mechanism | Scope | Purpose |
|-------|-----------|-------|---------|
| **STM** | `SqliteSaver` checkpointer | Per-conversation thread | Auto-save/restore graph state every step; survives server restarts |
| **LTM** | `InMemoryStore` (LangGraph Store API) | Cross-thread per-student | Persist facts, preferences, weaknesses across sessions |
| **Semantic** | ChromaDB vector store | Cross-thread per-student | Similarity retrieval for RAG-grounded explanations |
| **Relational** | SQLite `memories` table | Cross-thread per-student | Structured memory queries by type |

### Tech Stack

| Layer | Technology |
|-------|-----------|
| **LLM** | Google Gemini (`gemini-2.5-flash`) via `langchain-google-genai` |
| **Agent Orchestration** | LangGraph (StateGraph with conditional routing) |
| **Backend API** | FastAPI + Uvicorn |
| **Database** | SQLite + SQLAlchemy (PostgreSQL-ready via env var) |
| **Vector Store** | ChromaDB (local) |
| **Math Engine** | SymPy (symbolic evaluation) |
| **Search** | Tavily API (resource recommendations) |
| **Observability** | LangSmith tracing |
| **Frontend** | Next.js 16 + TypeScript + TailwindCSS |
| **Charts** | Recharts (radar, bar, area) |
| **Skill Tree Viz** | React Flow + dagre layout |
| **Frontend Testing** | Vitest + React Testing Library |

---

## 📂 Project Structure

```
adaptive-learning-companion/
├── backend/app/
│   ├── main.py                FastAPI entry, CORS, lifespan, router mounts
│   ├── config.py              pydantic-settings (env vars, API keys, LangSmith)
│   ├── database.py            SQLAlchemy engine, SessionLocal, init_db()
│   ├── auth.py                Simplified mock auth (in-memory token store)
│   ├── models/                ORM: Student, Skill, Session, Memory, seed.py
│   ├── schemas/               Pydantic: ChatRequest/Response, ProgressSummary, etc.
│   ├── services/              Business logic: student, skill, session, memory
│   ├── routers/
│   │   ├── auth.py            POST /login, GET /me, POST /logout
│   │   ├── chat.py            POST /chat (main conversational endpoint)
│   │   ├── students.py        CRUD /students
│   │   └── progress.py        GET /summary, /skills, /sessions
│   └── agents/
│       ├── state.py           ALCState TypedDict (shared graph state)
│       ├── graph.py           LangGraph StateGraph builder + get_graph()
│       ├── checkpointer.py    SqliteSaver (STM) + InMemoryStore (LTM)
│       ├── nodes/             diagnostician, curriculum, tutor, evaluator,
│       │                      question_generator, reflection, memory_saver,
│       │                      recommend
│       └── tools/             python_repl, math_evaluator,
│                              curriculum_fetcher, resource_search (Tavily)
├── frontend/
│   ├── src/app/
│   │   ├── login/page.tsx     Name-based login (mock auth)
│   │   ├── chat/page.tsx      Chat UI (markdown + LaTeX + resource cards)
│   │   ├── dashboard/page.tsx Stats, charts, session history
│   │   └── skills/page.tsx    Interactive React Flow skill tree
│   ├── src/components/        Sidebar, AppShell, MobileHeader, chat/,
│   │                          dashboard/, skills/ component groups
│   ├── src/context/           AuthProvider, StudentProvider
│   └── src/lib/               Typed API client, types, utilities
├── tests/                     84+ pytest tests (unit, integration, e2e)
├── spec.md                    Full specification document
├── todo.md                    Phase-by-phase task tracker
└── .env.example               Environment variable template
```

---

## 🛠️ Setup & Installation

### Prerequisites

- **Python 3.12+** (with `uv` package manager recommended)
- **Node.js 18+** (for the frontend)
- **Google Gemini API Key** ([Get one free](https://aistudio.google.com/apikey))

### 1. Clone & Install Backend

```bash
git clone https://github.com/your-username/adaptive-learning-companion.git
cd adaptive-learning-companion

# Install Python dependencies
uv sync

# Or with pip
pip install -e .
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your API keys:
#   GOOGLE_API_KEY="your-key"
#   TAVILY_API_KEY="your-key"       (optional, mock fallback available)
#   LANGSMITH_API_KEY="your-key"    (optional, for tracing)
```

### 3. Start the Backend

```bash
# From the project root
uvicorn backend.app.main:app --reload --port 8000
```

You should see:
```
✅ Database tables ready.
📊 LangSmith tracing enabled → project: adaptive-learning-companion
```

### 4. Install & Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000** → enter your name → start learning!

---

## 📡 API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/login` | Login by name (creates account if needed) → returns Bearer token |
| `GET` | `/api/auth/me` | Get current authenticated student |
| `POST` | `/api/auth/logout` | Revoke session token |

### Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat` | Send a message to the AI tutor |

**Request:**
```json
{
  "student_id": 1,
  "message": "Teach me about derivatives",
  "topic": "Calculus",
  "reset": false
}
```

**Response:**
```json
{
  "response": "Great question! Let's start by thinking about what happens when...",
  "current_topic": "Calculus",
  "current_difficulty": "easy",
  "learning_style": "visual",
  "mastery_score": 35.0,
  "session_id": 1,
  "recommended_resources": null
}
```

### Progress
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/progress/{id}/summary` | Dashboard stats (mastery, strongest/weakest skill) |
| `GET` | `/api/progress/{id}/skills` | Hierarchical skill tree with mastery scores |
| `GET` | `/api/progress/{id}/sessions` | Session history |

### Students
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/students` | Create a new student |
| `GET` | `/api/students` | List all students |
| `GET` | `/api/students/{id}` | Get a single student |

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |

---

## 🧪 Testing

### Backend (84 tests)

```bash
# Run all backend tests
.venv/Scripts/python -m pytest tests/ -q

# Run only fast tests (skip LLM-dependent ones)
.venv/Scripts/python -m pytest tests/ -q -m "not llm"
```

Tests cover: database models, services, API endpoints, agent tools, agent nodes, graph routing, memory saver, ChromaDB integration, checkpointer STM/LTM, and end-to-end flows.

### Frontend (7 tests)

```bash
cd frontend
npm run test
```

Component tests for `ChatInput` (submission, empty state, keyboard, disabled) and `StatsCards` (null state, populated values) using Vitest + React Testing Library.

---

## 📊 Math Skill Tree

Every student gets a 19-node hierarchical skill tree, seeded on creation:

```
Mathematics (root)
├── Algebra
│   ├── Linear Equations
│   ├── Quadratic Equations
│   ├── Functions
│   └── Polynomials
├── Calculus
│   ├── Limits
│   ├── Derivatives
│   ├── Integrals
│   └── Chain Rule
├── Trigonometry
│   ├── Trig Functions
│   ├── Trig Identities
│   └── Inverse Trig Functions
└── Statistics
    ├── Mean/Median/Mode
    ├── Probability
    └── Standard Deviation
```

Mastery scores (0–100) update automatically based on quiz performance evaluated by SymPy.

---

## 🔧 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | ✅ | Google Gemini API key |
| `LLM_MODEL` | No | Model name (default: `gemini-2.5-flash`) |
| `TAVILY_API_KEY` | No | Tavily search API key (mock fallback if missing) |
| `DATABASE_URL` | No | SQLAlchemy URL (default: `sqlite:///./learnmate.db`) |
| `CHROMA_PATH` | No | ChromaDB storage path (default: `./chroma_db`) |
| `LANGSMITH_TRACING` | No | Set to `true` to enable LangSmith tracing |
| `LANGSMITH_API_KEY` | No | LangSmith API key |
| `LANGSMITH_PROJECT` | No | LangSmith project name |

---

## 🗺️ Development Phases

| Phase | Status | Highlights |
|-------|--------|------------|
| **1. Backend Foundation** | ✅ Complete | FastAPI, SQLAlchemy models, services, API endpoints, agent tools |
| **2. Enhanced Agent Pipeline** | ✅ Complete | Conditional routing, evaluator, question generator, reflection, memory saver |
| **3. Memory Systems + RAG** | ✅ Complete | ChromaDB, long-term memory, Tavily search, skill prerequisites |
| **4. Frontend Dashboard** | ✅ Complete | Next.js 16, chat UI, dashboard charts, React Flow skill tree |
| **5. Testing & Polish** | ✅ Complete | Vitest, responsive layout, resource cards, learning style improvements |
| **6. Auth + Deploy** | 🔶 In Progress | LangSmith ✅, Mock Auth ✅, Evaluation suite & Docker pending |
| **7. LangGraph Memory** | ✅ Complete | SqliteSaver STM, InMemoryStore LTM, cross-thread memory, checkpointer tests |

---

## 📜 License

MIT
