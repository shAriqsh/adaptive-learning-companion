/* ──────────────────────────────────────────────────────────────────────────
 * TypeScript interfaces — mirrors backend Pydantic schemas exactly.
 * ────────────────────────────────────────────────────────────────────────── */

/** POST /api/students — request body */
export interface StudentCreate {
  name: string;
  email?: string | null;
}

/** Student record returned by the API */
export interface Student {
  id: number;
  name: string;
  email: string | null;
  created_at: string; // ISO datetime
}

/** POST /api/chat — request body */
export interface ChatRequest {
  student_id: number;
  message: string;
  topic?: string | null;
  reset?: boolean;
}

/** Resource item returned by Tavily search */
export interface ResourceItem {
  title: string;
  url: string;
  description?: string;
  type?: string; // "article" | "video" | "course" etc.
}

/** POST /api/chat — response */
export interface ChatResponse {
  response: string;
  current_topic: string;
  current_difficulty: string;
  learning_style: string;
  mastery_score: number | null;
  session_id: number | null;
  recommended_resources: ResourceItem[] | null;
}

/** GET /api/progress/{id}/summary */
export interface ProgressSummary {
  total_sessions: number;
  topics_studied: string[];
  overall_mastery: number;
  strongest_skill: string;
  weakest_skill: string;
  mastery_data: MasteryEntry[];
}

export interface MasteryEntry {
  name: string;
  score: number;
}

/** GET /api/progress/{id}/skills — recursive tree node */
export interface SkillNode {
  id: number;
  name: string;
  mastery_score: number;
  parent_id: number | null;
  children: SkillNode[];
}

/** GET /api/progress/{id}/sessions */
export interface SessionSummary {
  id: number;
  topic: string;
  summary: string | null;
  started_at: string; // ISO datetime
  ended_at: string | null; // ISO datetime
}

/** Local chat message for the UI */
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  resources?: ResourceItem[];
}

/** POST /api/auth/login — request body */
export interface LoginRequest {
  name: string;
  email?: string | null;
}

/** Auth student info returned by /api/auth/login and /api/auth/me */
export interface AuthStudent {
  id: number;
  name: string;
  email: string | null;
}

/** POST /api/auth/login — response */
export interface AuthResponse {
  token: string;
  student: AuthStudent;
}
