"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
  MessageSquare,
  LayoutDashboard,
  GitBranch,
  Plus,
  GraduationCap,
  ChevronDown,
  X,
  LogOut,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useStudent } from "@/context/student-context";
import { useAuth } from "@/context/auth-context";

const NAV_ITEMS = [
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/skills", label: "Skill Tree", icon: GitBranch },
];

interface SidebarProps {
  mobileOpen?: boolean;
  onMobileClose?: () => void;
}

export function Sidebar({ mobileOpen, onMobileClose }: SidebarProps) {
  const pathname = usePathname();
  const { students, activeStudent, setActiveStudent, addStudent, loading } =
    useStudent();
  const { logout: logoutAuth } = useAuth();
  const [showStudents, setShowStudents] = useState(false);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      await addStudent(newName.trim());
      setNewName("");
    } catch (err) {
      console.error("Failed to create student:", err);
    } finally {
      setCreating(false);
    }
  };

  const handleNavClick = () => {
    // Close mobile sidebar on navigation
    onMobileClose?.();
  };

  return (
    <>
      {/* ── Backdrop overlay (mobile only) ──────────────────────── */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={onMobileClose}
        />
      )}

      {/* ── Sidebar ─────────────────────────────────────────────── */}
      <aside
        className={cn(
          "fixed left-0 top-0 z-50 flex h-screen w-64 flex-col border-r border-white/10 bg-gray-950/95 backdrop-blur-xl transition-transform duration-300 ease-in-out",
          // Desktop: always visible
          "lg:translate-x-0",
          // Mobile: slide in/out
          mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        {/* ── Logo + Close button ─────────────────────────────────── */}
        <div className="flex items-center justify-between border-b border-white/10 px-5 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 shadow-lg shadow-violet-500/25">
              <GraduationCap className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight text-white">
                LearnMate
              </h1>
              <p className="text-[11px] font-medium uppercase tracking-widest text-violet-400">
                AI Tutor
              </p>
            </div>
          </div>
          {/* Close button — mobile only */}
          <button
            onClick={onMobileClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-gray-500 transition-colors hover:bg-white/5 hover:text-gray-300 lg:hidden"
            aria-label="Close menu"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* ── Navigation ───────────────────────────────────────────── */}
        <nav className="flex-1 space-y-1 px-3 py-4">
          {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                onClick={handleNavClick}
                className={cn(
                  "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200",
                  active
                    ? "bg-violet-500/15 text-violet-300 shadow-sm shadow-violet-500/10"
                    : "text-gray-400 hover:bg-white/5 hover:text-gray-200"
                )}
              >
                <Icon
                  className={cn(
                    "h-4.5 w-4.5 transition-colors",
                    active
                      ? "text-violet-400"
                      : "text-gray-500 group-hover:text-gray-400"
                  )}
                />
                {label}
                {active && (
                  <div className="ml-auto h-1.5 w-1.5 rounded-full bg-violet-400 shadow-sm shadow-violet-400/50" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* ── Student Selector ─────────────────────────────────────── */}
        <div className="border-t border-white/10 p-3">
          <button
            onClick={() => setShowStudents(!showStudents)}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-gray-300 transition-colors hover:bg-white/5"
          >
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-emerald-400 to-cyan-500 text-xs font-bold text-white">
              {activeStudent?.name?.[0]?.toUpperCase() ?? "?"}
            </div>
            <span className="flex-1 truncate text-left">
              {loading
                ? "Loading..."
                : activeStudent?.name ?? "Select Student"}
            </span>
            <ChevronDown
              className={cn(
                "h-4 w-4 text-gray-500 transition-transform",
                showStudents && "rotate-180"
              )}
            />
          </button>

          {showStudents && (
            <div className="mt-2 space-y-1 rounded-lg border border-white/10 bg-gray-900/90 p-2">
              {students.map((s) => (
                <button
                  key={s.id}
                  onClick={() => {
                    setActiveStudent(s);
                    setShowStudents(false);
                  }}
                  className={cn(
                    "w-full rounded-md px-3 py-1.5 text-left text-sm transition-colors",
                    s.id === activeStudent?.id
                      ? "bg-violet-500/20 text-violet-300"
                      : "text-gray-400 hover:bg-white/5 hover:text-gray-200"
                  )}
                >
                  {s.name}
                </button>
              ))}

              {/* New student form */}
              <div className="flex gap-1.5 pt-1">
                <input
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleCreate()}
                  placeholder="New student..."
                  className="flex-1 rounded-md border border-white/10 bg-white/5 px-2.5 py-1.5 text-xs text-gray-200 placeholder:text-gray-500 focus:border-violet-500/50 focus:outline-none focus:ring-1 focus:ring-violet-500/25"
                />
                <button
                  onClick={handleCreate}
                  disabled={creating || !newName.trim()}
                  className="rounded-md bg-violet-500/20 p-1.5 text-violet-400 transition-colors hover:bg-violet-500/30 disabled:opacity-50"
                >
                  <Plus className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* ── Logout ──────────────────────────────────────────────── */}
        <div className="border-t border-white/10 p-3">
          <button
            onClick={() => logoutAuth()}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-gray-500 transition-colors hover:bg-red-500/10 hover:text-red-400"
          >
            <LogOut className="h-4 w-4" />
            Sign Out
          </button>
        </div>
      </aside>
    </>
  );
}
