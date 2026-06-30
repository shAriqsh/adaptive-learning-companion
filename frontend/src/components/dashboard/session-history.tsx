"use client";

import { Clock, BookOpen } from "lucide-react";
import type { SessionSummary } from "@/lib/types";

interface SessionHistoryProps {
  sessions: SessionSummary[];
}

export function SessionHistory({ sessions }: SessionHistoryProps) {
  if (sessions.length === 0) {
    return (
      <div className="rounded-xl border border-white/10 bg-gray-900/40 p-5">
        <h3 className="mb-4 text-sm font-semibold text-gray-200">
          Session History
        </h3>
        <p className="py-8 text-center text-sm text-gray-500">
          No sessions yet. Start chatting to create your first session!
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-white/10 bg-gray-900/40 p-5">
      <h3 className="mb-4 text-sm font-semibold text-gray-200">
        Recent Sessions
      </h3>
      <div className="space-y-2">
        {sessions.map((session) => (
          <div
            key={session.id}
            className="group flex items-start gap-3 rounded-lg border border-white/5 bg-white/[0.02] p-3 transition-colors hover:border-white/10 hover:bg-white/[0.04]"
          >
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-violet-500/10">
              <BookOpen className="h-4 w-4 text-violet-400" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-medium text-gray-200">
                  {session.topic}
                </p>
                <span className="flex shrink-0 items-center gap-1 text-[11px] text-gray-500">
                  <Clock className="h-3 w-3" />
                  {new Date(session.started_at).toLocaleDateString(undefined, {
                    month: "short",
                    day: "numeric",
                  })}
                </span>
              </div>
              {session.summary && (
                <p className="mt-1 line-clamp-2 text-xs text-gray-400">
                  {session.summary}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
