"use client";

import { useState } from "react";
import { GraduationCap, ArrowRight, Sparkles, BookOpen, Brain, TrendingUp } from "lucide-react";
import { useAuth } from "@/context/auth-context";

export default function LoginPage() {
  const { login } = useAuth();
  const [name, setName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setSubmitting(true);
    setError(null);
    try {
      await login(name.trim());
    } catch (err) {
      setError(
        "Could not connect to the server. Make sure the backend is running at localhost:8000."
      );
      console.error("Login error:", err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-950 px-4">
      {/* Background accents */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -left-32 -top-32 h-96 w-96 rounded-full bg-violet-500/10 blur-3xl" />
        <div className="absolute -bottom-32 -right-32 h-96 w-96 rounded-full bg-indigo-500/10 blur-3xl" />
      </div>

      <div className="relative z-10 w-full max-w-md">
        {/* Logo + Title */}
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 shadow-lg shadow-violet-500/25">
            <GraduationCap className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white">
            LearnMate AI
          </h1>
          <p className="mt-2 text-sm text-gray-400">
            Your intelligent math tutor — powered by AI
          </p>
        </div>

        {/* Login Card */}
        <div className="rounded-2xl border border-white/10 bg-gray-900/80 p-8 shadow-xl backdrop-blur-xl">
          <h2 className="mb-1 text-lg font-semibold text-gray-200">
            Get Started
          </h2>
          <p className="mb-6 text-sm text-gray-500">
            Enter your name to start learning. No password needed.
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="student-name"
                className="mb-1.5 block text-xs font-medium text-gray-400"
              >
                Your Name
              </label>
              <input
                id="student-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Alex, Sarah, Jordan..."
                autoFocus
                className="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-3 text-sm text-gray-200 placeholder:text-gray-600 focus:border-violet-500/50 focus:outline-none focus:ring-2 focus:ring-violet-500/20"
              />
            </div>

            {error && (
              <p className="rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-xs text-red-400">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={submitting || !name.trim()}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 px-4 py-3 text-sm font-medium text-white shadow-lg shadow-violet-500/25 transition-all duration-200 hover:from-violet-500 hover:to-indigo-500 hover:shadow-violet-500/40 disabled:opacity-50 disabled:shadow-none"
            >
              {submitting ? (
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
              ) : (
                <>
                  Start Learning
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </form>
        </div>

        {/* Feature badges */}
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          {[
            { icon: Sparkles, label: "AI-Powered Tutoring" },
            { icon: BookOpen, label: "Adaptive Curriculum" },
            { icon: Brain, label: "Learning Style Detection" },
            { icon: TrendingUp, label: "Progress Tracking" },
          ].map(({ icon: Icon, label }) => (
            <span
              key={label}
              className="inline-flex items-center gap-1.5 rounded-full border border-white/5 bg-white/[0.03] px-3 py-1.5 text-[11px] text-gray-500"
            >
              <Icon className="h-3 w-3" />
              {label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
