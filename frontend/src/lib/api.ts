/* ──────────────────────────────────────────────────────────────────────────
 * API Client — typed wrappers around every backend endpoint.
 *
 * Base URL defaults to http://localhost:8000 but can be overridden via
 * the NEXT_PUBLIC_API_URL environment variable.
 * ────────────────────────────────────────────────────────────────────────── */

import type {
  AuthResponse,
  ChatResponse,
  ProgressSummary,
  SessionSummary,
  SkillNode,
  Student,
  StudentCreate,
  AuthStudent,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Token Management ────────────────────────────────────────────────────

const TOKEN_KEY = "learnmate_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

// ── Helpers ──────────────────────────────────────────────────────────────

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  const res = await fetch(`${API_BASE}${path}`, {
    headers,
    ...options,
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${body || res.statusText}`);
  }

  return res.json() as Promise<T>;
}

// ── Auth ─────────────────────────────────────────────────────────────────

export async function login(name: string, email?: string): Promise<AuthResponse> {
  const data = await request<AuthResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ name, email: email || undefined }),
  });
  setToken(data.token);
  return data;
}

export async function getMe(): Promise<AuthStudent> {
  return request<AuthStudent>("/api/auth/me");
}

export async function logout(): Promise<void> {
  try {
    await request<{ detail: string }>("/api/auth/logout", { method: "POST" });
  } catch {
    // ignore logout errors
  }
  clearToken();
}

// ── Students ─────────────────────────────────────────────────────────────

export async function createStudent(data: StudentCreate): Promise<Student> {
  return request<Student>("/api/students", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getStudents(): Promise<Student[]> {
  return request<Student[]>("/api/students");
}

export async function getStudent(id: number): Promise<Student> {
  return request<Student>(`/api/students/${id}`);
}

// ── Chat ─────────────────────────────────────────────────────────────────

export async function sendMessage(
  studentId: number,
  message: string,
  topic?: string | null,
  reset?: boolean
): Promise<ChatResponse> {
  return request<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify({
      student_id: studentId,
      message,
      topic: topic ?? undefined,
      reset: reset ?? false,
    }),
  });
}

// ── Progress ─────────────────────────────────────────────────────────────

export async function getProgressSummary(
  studentId: number
): Promise<ProgressSummary> {
  return request<ProgressSummary>(
    `/api/progress/${studentId}/summary`
  );
}

export async function getSkillTree(
  studentId: number
): Promise<SkillNode[]> {
  return request<SkillNode[]>(
    `/api/progress/${studentId}/skills`
  );
}

export async function getSessions(
  studentId: number,
  limit = 20
): Promise<SessionSummary[]> {
  return request<SessionSummary[]>(
    `/api/progress/${studentId}/sessions?limit=${limit}`
  );
}
