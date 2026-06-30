"use client";

import {
  BookOpen,
  TrendingUp,
  Award,
  AlertTriangle,
} from "lucide-react";
import type { ProgressSummary } from "@/lib/types";

interface StatsCardsProps {
  summary: ProgressSummary | null;
}

const CARDS = [
  {
    label: "Total Sessions",
    key: "total_sessions" as const,
    icon: BookOpen,
    gradient: "from-violet-500 to-indigo-600",
    border: "border-violet-500/20",
    bg: "bg-violet-500/5",
    format: (v: number) => v.toString(),
  },
  {
    label: "Overall Mastery",
    key: "overall_mastery" as const,
    icon: TrendingUp,
    gradient: "from-emerald-400 to-cyan-500",
    border: "border-emerald-500/20",
    bg: "bg-emerald-500/5",
    format: (v: number) => `${v.toFixed(1)}%`,
  },
  {
    label: "Strongest Skill",
    key: "strongest_skill" as const,
    icon: Award,
    gradient: "from-amber-400 to-orange-500",
    border: "border-amber-500/20",
    bg: "bg-amber-500/5",
    format: (v: string) => v || "—",
  },
  {
    label: "Weakest Skill",
    key: "weakest_skill" as const,
    icon: AlertTriangle,
    gradient: "from-rose-400 to-pink-500",
    border: "border-rose-500/20",
    bg: "bg-rose-500/5",
    format: (v: string) => v || "—",
  },
];

export function StatsCards({ summary }: StatsCardsProps) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {CARDS.map(({ label, key, icon: Icon, gradient, border, bg, format }) => {
        const raw = summary?.[key];
        const value =
          raw !== undefined && raw !== null ? format(raw as never) : "—";

        return (
          <div
            key={key}
            className={`group relative overflow-hidden rounded-xl border ${border} ${bg} p-5 transition-all duration-300 hover:border-opacity-40`}
          >
            {/* Gradient accent line */}
            <div
              className={`absolute left-0 top-0 h-1 w-full bg-gradient-to-r ${gradient} opacity-60`}
            />

            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-medium uppercase tracking-wider text-gray-500">
                  {label}
                </p>
                <p className="mt-2 text-2xl font-bold text-gray-100">
                  {value}
                </p>
              </div>
              <div
                className={`flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br ${gradient} opacity-80 shadow-lg`}
              >
                <Icon className="h-5 w-5 text-white" />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
