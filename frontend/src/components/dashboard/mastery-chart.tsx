"use client";

import { useState } from "react";
import { BarChart3, Radar as RadarIcon } from "lucide-react";
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
} from "recharts";
import { cn } from "@/lib/utils";
import type { MasteryEntry } from "@/lib/types";

interface MasteryChartProps {
  data: MasteryEntry[];
}

function getMasteryColor(score: number): string {
  if (score >= 70) return "#34d399"; // green
  if (score >= 40) return "#fbbf24"; // yellow
  return "#f87171"; // red
}

export function MasteryChart({ data }: MasteryChartProps) {
  const [view, setView] = useState<"radar" | "bar">("radar");

  // Filter out the root "Mathematics" node for cleaner charts
  const chartData = data.filter((d) => d.name !== "Mathematics");

  if (chartData.length === 0) {
    return (
      <div className="flex h-80 items-center justify-center text-sm text-gray-500">
        No mastery data yet. Start a chat session!
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-white/10 bg-gray-900/40 p-5">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-200">
          Skill Mastery Overview
        </h3>
        <div className="flex gap-1 rounded-lg border border-white/10 bg-gray-900/60 p-0.5">
          <button
            onClick={() => setView("radar")}
            className={cn(
              "flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs transition-colors",
              view === "radar"
                ? "bg-violet-500/20 text-violet-300"
                : "text-gray-500 hover:text-gray-300"
            )}
          >
            <RadarIcon className="h-3 w-3" />
            Radar
          </button>
          <button
            onClick={() => setView("bar")}
            className={cn(
              "flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs transition-colors",
              view === "bar"
                ? "bg-violet-500/20 text-violet-300"
                : "text-gray-500 hover:text-gray-300"
            )}
          >
            <BarChart3 className="h-3 w-3" />
            Bar
          </button>
        </div>
      </div>

      {/* Chart */}
      <div className={cn("transition-all duration-300", view === "bar" ? "h-[500px]" : "h-80")}>
        <ResponsiveContainer width="100%" height="100%">
          {view === "radar" ? (
            <RadarChart data={chartData} cx="50%" cy="50%" outerRadius="70%">
              <PolarGrid stroke="rgba(255,255,255,0.08)" />
              <PolarAngleAxis
                dataKey="name"
                tick={{ fill: "#9ca3af", fontSize: 11 }}
              />
              <PolarRadiusAxis
                angle={30}
                domain={[0, 100]}
                tick={{ fill: "#6b7280", fontSize: 10 }}
              />
              <Radar
                name="Mastery"
                dataKey="score"
                stroke="#8b5cf6"
                fill="#8b5cf6"
                fillOpacity={0.25}
                strokeWidth={2}
              />
            </RadarChart>
          ) : (
            <BarChart
              data={chartData}
              layout="vertical"
              margin={{ top: 5, right: 20, bottom: 5, left: 10 }}
            >
              <XAxis
                type="number"
                domain={[0, 100]}
                tick={{ fill: "#6b7280", fontSize: 11 }}
                axisLine={{ stroke: "rgba(255,255,255,0.08)" }}
              />
              <YAxis
                type="category"
                dataKey="name"
                tick={{ fill: "#9ca3af", fontSize: 10 }}
                axisLine={false}
                tickLine={false}
                width={150}
                interval={0}
              />
              <Tooltip
                contentStyle={{
                  background: "#1f2937",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: "8px",
                  fontSize: "12px",
                  color: "#e5e7eb",
                }}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                formatter={(value: any) => [`${Number(value).toFixed(1)}%`, "Mastery"]}
              />
              <Bar dataKey="score" radius={[0, 4, 4, 0]} barSize={16}>
                {chartData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={getMasteryColor(entry.score)}
                  />
                ))}
              </Bar>
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
