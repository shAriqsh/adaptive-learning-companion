"use client";

import { useEffect, useState } from "react";
import { Loader2, Sparkles } from "lucide-react";
import { useStudent } from "@/context/student-context";
import { getProgressSummary, getSessions } from "@/lib/api";
import type { ProgressSummary, SessionSummary } from "@/lib/types";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { MasteryChart } from "@/components/dashboard/mastery-chart";
import { SessionHistory } from "@/components/dashboard/session-history";

export default function DashboardPage() {
  const { activeStudent } = useStudent();
  const [summary, setSummary] = useState<ProgressSummary | null>(null);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!activeStudent) return;

    let cancelled = false;

    Promise.all([
      getProgressSummary(activeStudent.id),
      getSessions(activeStudent.id),
    ])
      .then(([sum, sess]) => {
        if (cancelled) return;
        setSummary(sum);
        setSessions(sess);
        setError(null);
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error("Dashboard load error:", err);
        setError("Failed to load dashboard data. Is the backend running?");
        setLoading(false);
      });

    return () => { cancelled = true; };
  }, [activeStudent]);

  if (!activeStudent) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <Sparkles className="mx-auto mb-4 h-12 w-12 text-violet-400 opacity-50" />
          <h2 className="text-xl font-semibold text-gray-300">
            No Student Selected
          </h2>
          <p className="mt-2 text-sm text-gray-500">
            Select a student to view their dashboard.
          </p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-violet-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 p-6 text-center">
          <p className="text-sm text-rose-300">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-6">
      <div className="mx-auto max-w-6xl space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-gray-100">
            {activeStudent.name}&apos;s Dashboard
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Track your learning progress and skill mastery
          </p>
        </div>

        {/* Stats Cards */}
        <StatsCards summary={summary} />

        {/* Charts + History Grid */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <MasteryChart data={summary?.mastery_data ?? []} />
          </div>
          <div>
            <SessionHistory sessions={sessions} />
          </div>
        </div>
      </div>
    </div>
  );
}
