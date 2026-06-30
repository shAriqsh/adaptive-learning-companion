"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { login as apiLogin, logout as apiLogout, getMe, getToken, clearToken } from "@/lib/api";
import type { AuthStudent } from "@/lib/types";

interface AuthContextValue {
  /** The authenticated student, or null if not logged in */
  user: AuthStudent | null;
  /** True while we're checking the stored token on mount */
  loading: boolean;
  /** Log in by name (creates account if needed) */
  login: (name: string, email?: string) => Promise<void>;
  /** Log out and clear token */
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthStudent | null>(null);
  const [loading, setLoading] = useState(true);

  // On mount, check if there's a stored token and validate it
  useEffect(() => {
    const token = getToken();
    if (!token) {
      setLoading(false);
      return;
    }

    getMe()
      .then((student) => {
        setUser(student);
      })
      .catch(() => {
        // Token invalid or expired — clear it
        clearToken();
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (name: string, email?: string) => {
    const res = await apiLogin(name, email);
    setUser(res.student);
  }, []);

  const logout = useCallback(async () => {
    await apiLogout();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
