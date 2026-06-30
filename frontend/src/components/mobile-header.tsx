"use client";

import { Menu, GraduationCap } from "lucide-react";

interface MobileHeaderProps {
  onMenuToggle: () => void;
}

export function MobileHeader({ onMenuToggle }: MobileHeaderProps) {
  return (
    <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-white/10 bg-gray-950/90 px-4 py-3 backdrop-blur-xl lg:hidden">
      <button
        onClick={onMenuToggle}
        className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 text-gray-400 transition-colors hover:bg-white/5 hover:text-gray-200"
        aria-label="Toggle menu"
      >
        <Menu className="h-5 w-5" />
      </button>
      <div className="flex items-center gap-2">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600">
          <GraduationCap className="h-4 w-4 text-white" />
        </div>
        <span className="text-sm font-bold text-white">LearnMate</span>
      </div>
    </header>
  );
}
