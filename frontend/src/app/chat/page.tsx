"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  RotateCcw,
  BookOpen,
  Zap,
  Brain,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useStudent } from "@/context/student-context";
import { sendMessage } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";
import { MessageBubble, TypingIndicator } from "@/components/chat/message-bubble";
import { ChatInput } from "@/components/chat/chat-input";

const MATH_TOPICS = [
  "Algebra",
  "Calculus",
  "Trigonometry",
  "Statistics",
  "Linear Equations",
  "Derivatives",
  "Integrals",
  "Probability",
];

export default function ChatPage() {
  const { activeStudent } = useStudent();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [currentTopic, setCurrentTopic] = useState("General");
  const [difficulty, setDifficulty] = useState("easy");
  const [learningStyle, setLearningStyle] = useState("unknown");
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);
  const [masteryScore, setMasteryScore] = useState<number | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const handleSend = useCallback(
    async (text: string) => {
      if (!activeStudent) return;

      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: text,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setLoading(true);

      try {
        const res = await sendMessage(
          activeStudent.id,
          text,
          selectedTopic
        );

        const aiMsg: ChatMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: res.response,
          timestamp: new Date(),
          resources: res.recommended_resources ?? undefined,
        };
        setMessages((prev) => [...prev, aiMsg]);
        setCurrentTopic(res.current_topic);
        setDifficulty(res.current_difficulty);
        setLearningStyle(res.learning_style);
        setMasteryScore(res.mastery_score);
      } catch (err) {
        const errorMsg: ChatMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          content:
            "⚠️ Sorry, I had trouble connecting to the server. Please make sure the backend is running at `localhost:8000`.",
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errorMsg]);
        console.error("Chat error:", err);
      } finally {
        setLoading(false);
      }
    },
    [activeStudent, selectedTopic]
  );

  const handleReset = useCallback(async () => {
    if (!activeStudent) return;
    try {
      await sendMessage(activeStudent.id, "", null, true);
    } catch {
      // ignore reset errors
    }
    setMessages([]);
    setCurrentTopic("General");
    setDifficulty("easy");
    setLearningStyle("unknown");
    setMasteryScore(null);
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
            Create or select a student from the sidebar to start learning.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col">
      {/* ── Header with metadata badges ─────────────────────────── */}
      <header className="flex items-center justify-between border-b border-white/10 bg-gray-950/80 px-6 py-3 backdrop-blur-xl">
        <div className="flex items-center gap-4">
          <h2 className="text-lg font-semibold text-gray-200">
            Chat with LearnMate
          </h2>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-violet-500/30 bg-violet-500/10 px-2.5 py-0.5 text-xs font-medium text-violet-300">
              <BookOpen className="h-3 w-3" />
              {currentTopic}
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-0.5 text-xs font-medium text-amber-300">
              <Zap className="h-3 w-3" />
              {difficulty}
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-2.5 py-0.5 text-xs font-medium text-cyan-300">
              <Brain className="h-3 w-3" />
              {learningStyle}
            </span>
            {masteryScore !== null && (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-xs font-medium text-emerald-300">
                <TrendingUp className="h-3 w-3" />
                {masteryScore.toFixed(0)}%
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* Topic selector */}
          <select
            value={selectedTopic ?? ""}
            onChange={(e) =>
              setSelectedTopic(e.target.value || null)
            }
            className="rounded-lg border border-white/10 bg-gray-900/60 px-3 py-1.5 text-xs text-gray-300 focus:border-violet-500/50 focus:outline-none"
          >
            <option value="">Auto topic</option>
            {MATH_TOPICS.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
          <button
            onClick={handleReset}
            className="flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-xs text-gray-400 transition-colors hover:bg-white/5 hover:text-gray-200"
          >
            <RotateCcw className="h-3 w-3" />
            Reset
          </button>
        </div>
      </header>

      {/* ── Messages area ──────────────────────────────────────── */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto max-w-3xl space-y-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500/20 to-indigo-500/20 shadow-lg shadow-violet-500/5">
                <Sparkles className="h-8 w-8 text-violet-400" />
              </div>
              <h3 className="text-xl font-semibold text-gray-200">
                Hi {activeStudent.name}! 👋
              </h3>
              <p className="mt-2 max-w-md text-sm text-gray-400">
                I&apos;m your AI math tutor. Ask me about algebra, calculus,
                trigonometry, or statistics. I&apos;ll adapt to your learning
                style!
              </p>
              <div className="mt-6 flex flex-wrap justify-center gap-2">
                {[
                  "Teach me about derivatives",
                  "What are linear equations?",
                  "Help me with probability",
                  "Explain trigonometric identities",
                ].map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => handleSend(suggestion)}
                    className={cn(
                      "rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs text-gray-300",
                      "transition-all duration-200 hover:border-violet-500/30 hover:bg-violet-500/10 hover:text-violet-300"
                    )}
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}

          {loading && <TypingIndicator />}
        </div>
      </div>

      {/* ── Input ──────────────────────────────────────────────── */}
      <ChatInput onSend={handleSend} disabled={loading} />
    </div>
  );
}
