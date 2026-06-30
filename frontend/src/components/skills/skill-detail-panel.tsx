"use client";

import { X, BookOpen, ArrowRight } from "lucide-react";
import { useRouter } from "next/navigation";
import type { SkillNode } from "@/lib/types";

interface SkillDetailPanelProps {
  skill: SkillNode | null;
  onClose: () => void;
}

function getMasteryLabel(score: number): string {
  if (score >= 80) return "Mastered";
  if (score >= 60) return "Proficient";
  if (score >= 40) return "Developing";
  if (score >= 20) return "Beginner";
  return "Not Started";
}

function getMasteryColor(score: number) {
  if (score >= 70) return "text-emerald-400";
  if (score >= 40) return "text-amber-400";
  return "text-rose-400";
}

export function SkillDetailPanel({ skill, onClose }: SkillDetailPanelProps) {
  const router = useRouter();

  if (!skill) return null;

  return (
    <div className="animate-fade-in-up absolute right-4 top-4 z-50 w-72 rounded-xl border border-white/10 bg-gray-900/95 p-5 shadow-2xl backdrop-blur-xl">
      {/* Close button */}
      <button
        onClick={onClose}
        className="absolute right-3 top-3 rounded-md p-1 text-gray-500 transition-colors hover:bg-white/5 hover:text-gray-300"
      >
        <X className="h-4 w-4" />
      </button>

      {/* Skill name */}
      <h3 className="text-lg font-bold text-gray-100">{skill.name}</h3>

      {/* Mastery score */}
      <div className="mt-3">
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-500">Mastery</span>
          <span className={`text-sm font-bold ${getMasteryColor(skill.mastery_score)}`}>
            {skill.mastery_score.toFixed(1)}%
          </span>
        </div>
        <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-white/10">
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{
              width: `${skill.mastery_score}%`,
              backgroundColor:
                skill.mastery_score >= 70
                  ? "#34d399"
                  : skill.mastery_score >= 40
                  ? "#fbbf24"
                  : "#f87171",
            }}
          />
        </div>
        <p className="mt-1 text-xs text-gray-500">
          {getMasteryLabel(skill.mastery_score)}
        </p>
      </div>

      {/* Children */}
      {skill.children && skill.children.length > 0 && (
        <div className="mt-4">
          <p className="text-xs font-medium text-gray-500">Sub-skills</p>
          <div className="mt-2 space-y-1.5">
            {skill.children.map((child) => (
              <div
                key={child.id}
                className="flex items-center justify-between rounded-md border border-white/5 bg-white/[0.02] px-3 py-1.5"
              >
                <span className="text-xs text-gray-300">{child.name}</span>
                <span
                  className={`text-[10px] font-bold ${getMasteryColor(child.mastery_score)}`}
                >
                  {child.mastery_score.toFixed(0)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Practice button */}
      <button
        onClick={() => router.push(`/chat`)}
        className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 px-4 py-2.5 text-sm font-medium text-white shadow-lg shadow-violet-500/20 transition-all duration-200 hover:shadow-violet-500/40"
      >
        <BookOpen className="h-4 w-4" />
        Practice {skill.name}
        <ArrowRight className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
