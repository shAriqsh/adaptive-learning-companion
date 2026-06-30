"use client";

import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
import { Bot, User } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/lib/types";
import { ResourceCards } from "./resource-cards";

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={cn(
        "animate-fade-in-up flex gap-3",
        isUser ? "flex-row-reverse" : "flex-row"
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
          isUser
            ? "bg-gradient-to-br from-emerald-400 to-cyan-500"
            : "bg-gradient-to-br from-violet-500 to-indigo-600"
        )}
      >
        {isUser ? (
          <User className="h-4 w-4 text-white" />
        ) : (
          <Bot className="h-4 w-4 text-white" />
        )}
      </div>

      {/* Bubble */}
      <div
        className={cn(
          "max-w-[75%] rounded-2xl px-4 py-3 text-sm",
          isUser
            ? "rounded-tr-sm bg-gradient-to-br from-violet-600/90 to-indigo-600/90 text-white"
            : "rounded-tl-sm border border-white/10 bg-gray-900/80 text-gray-200"
        )}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="prose-chat">
            <ReactMarkdown
              remarkPlugins={[remarkMath]}
              rehypePlugins={[rehypeKatex]}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}

        {/* Resource cards — shown below AI messages when available */}
        {!isUser && message.resources && message.resources.length > 0 && (
          <ResourceCards resources={message.resources} />
        )}

        <p
          className={cn(
            "mt-1.5 text-[10px]",
            isUser ? "text-white/50" : "text-gray-500"
          )}
        >
          {message.timestamp.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </p>
      </div>
    </div>
  );
}

export function TypingIndicator() {
  return (
    <div className="animate-fade-in-up flex gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600">
        <Bot className="h-4 w-4 text-white" />
      </div>
      <div className="rounded-2xl rounded-tl-sm border border-white/10 bg-gray-900/80 px-4 py-3">
        <div className="flex gap-1.5">
          <div className="typing-dot h-2 w-2 rounded-full bg-violet-400" />
          <div className="typing-dot h-2 w-2 rounded-full bg-violet-400" />
          <div className="typing-dot h-2 w-2 rounded-full bg-violet-400" />
        </div>
      </div>
    </div>
  );
}
