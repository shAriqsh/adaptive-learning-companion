"use client";

import { useEffect, useState } from "react";
import { Loader2, Sparkles } from "lucide-react";
import { useStudent } from "@/context/student-context";
import { getSkillTree } from "@/lib/api";
import type { SkillNode } from "@/lib/types";
import { SkillTree } from "@/components/skills/skill-tree";
import { SkillDetailPanel } from "@/components/skills/skill-detail-panel";

export default function SkillsPage() {
  const { activeStudent } = useStudent();
  const [tree, setTree] = useState<SkillNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSkill, setSelectedSkill] = useState<SkillNode | null>(null);

  useEffect(() => {
    if (!activeStudent) return;

    let cancelled = false;

    getSkillTree(activeStudent.id)
      .then((res) => {
        if (cancelled) return;
        setTree(res);
        setError(null);
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error("Skill tree load error:", err);
        setError("Failed to load skill tree. Is the backend running?");
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
            Select a student to view their skill tree.
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
    <div className="relative flex h-screen flex-col p-6">
      {/* Header */}
      <div className="mb-4">
        <h1 className="text-2xl font-bold text-gray-100">
          Math Skill Tree
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Click on any skill to see details. Colors indicate mastery:{" "}
          <span className="text-rose-400">red</span> ={" "}
          <span className="text-rose-400">&lt;40%</span>,{" "}
          <span className="text-amber-400">yellow</span> ={" "}
          <span className="text-amber-400">40-70%</span>,{" "}
          <span className="text-emerald-400">green</span> ={" "}
          <span className="text-emerald-400">&gt;70%</span>
        </p>
      </div>

      {/* Tree */}
      <div className="relative flex-1">
        <SkillTree tree={tree} onNodeClick={setSelectedSkill} />
        <SkillDetailPanel
          skill={selectedSkill}
          onClose={() => setSelectedSkill(null)}
        />
      </div>
    </div>
  );
}
