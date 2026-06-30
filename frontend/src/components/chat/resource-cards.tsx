"use client";

import { ExternalLink, BookOpen, Video, GraduationCap, FileText } from "lucide-react";
import type { ResourceItem } from "@/lib/types";

interface ResourceCardsProps {
  resources: ResourceItem[];
}

function getTypeIcon(type?: string) {
  switch (type?.toLowerCase()) {
    case "video":
      return <Video className="h-3.5 w-3.5" />;
    case "course":
      return <GraduationCap className="h-3.5 w-3.5" />;
    case "article":
      return <FileText className="h-3.5 w-3.5" />;
    default:
      return <BookOpen className="h-3.5 w-3.5" />;
  }
}

function getTypeBadgeColor(type?: string) {
  switch (type?.toLowerCase()) {
    case "video":
      return "border-rose-500/30 bg-rose-500/10 text-rose-300";
    case "course":
      return "border-emerald-500/30 bg-emerald-500/10 text-emerald-300";
    case "article":
      return "border-cyan-500/30 bg-cyan-500/10 text-cyan-300";
    default:
      return "border-violet-500/30 bg-violet-500/10 text-violet-300";
  }
}

export function ResourceCards({ resources }: ResourceCardsProps) {
  if (!resources || resources.length === 0) return null;

  return (
    <div className="mt-3 space-y-2">
      <p className="text-[10px] font-medium uppercase tracking-wider text-gray-500">
        📚 Recommended Resources
      </p>
      <div className="grid gap-2">
        {resources.map((resource, index) => (
          <a
            key={index}
            href={resource.url}
            target="_blank"
            rel="noopener noreferrer"
            className="group flex items-start gap-3 rounded-lg border border-white/10 bg-white/[0.03] p-3 transition-all duration-200 hover:border-violet-500/30 hover:bg-violet-500/5"
          >
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500/15 to-indigo-500/15 text-violet-400 transition-colors group-hover:from-violet-500/25 group-hover:to-indigo-500/25">
              {getTypeIcon(resource.type)}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <p className="truncate text-xs font-medium text-gray-200 group-hover:text-violet-300">
                  {resource.title}
                </p>
                <ExternalLink className="h-3 w-3 shrink-0 text-gray-600 transition-colors group-hover:text-violet-400" />
              </div>
              {resource.description && (
                <p className="mt-0.5 line-clamp-2 text-[11px] text-gray-500">
                  {resource.description}
                </p>
              )}
              {resource.type && (
                <span
                  className={`mt-1.5 inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium ${getTypeBadgeColor(resource.type)}`}
                >
                  {getTypeIcon(resource.type)}
                  {resource.type}
                </span>
              )}
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
