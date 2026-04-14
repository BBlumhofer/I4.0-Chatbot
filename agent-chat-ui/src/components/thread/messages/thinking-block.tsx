"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, Brain } from "lucide-react";
import { MarkdownText } from "../markdown-text";
import { motion, AnimatePresence } from "framer-motion";

interface ThinkingBlockProps {
  content: string;
  isStreaming?: boolean;
}

export function ThinkingBlock({ content, isStreaming }: ThinkingBlockProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="mb-2 overflow-hidden rounded-xl border" style={{ borderColor: "var(--thinking-border, #d8b4fe)", backgroundColor: "var(--thinking-bg, #faf5ff)" }}>
      <button
        type="button"
        onClick={() => setIsOpen((o) => !o)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition-colors"
        style={{ color: "var(--thinking-text, #7e22ce)" }}
      >
        <Brain className="size-4 shrink-0" />
        {isStreaming ? (
          <span className="flex items-center gap-1.5">
            Thinking
            <span className="inline-flex gap-0.5">
              <span
                className="size-1.5 animate-bounce rounded-full"
                style={{ backgroundColor: "var(--thinking-dot, #a855f7)", animationDelay: "0ms" }}
              />
              <span
                className="size-1.5 animate-bounce rounded-full"
                style={{ backgroundColor: "var(--thinking-dot, #a855f7)", animationDelay: "150ms" }}
              />
              <span
                className="size-1.5 animate-bounce rounded-full"
                style={{ backgroundColor: "var(--thinking-dot, #a855f7)", animationDelay: "300ms" }}
              />
            </span>
          </span>
        ) : (
          <span>Thought for a moment</span>
        )}
        <span className="ml-auto">
          {isOpen ? (
            <ChevronUp className="size-4" />
          ) : (
            <ChevronDown className="size-4" />
          )}
        </span>
      </button>
      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            key="thinking-content"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-4 py-3 text-sm" style={{ borderTopColor: "var(--thinking-border, #d8b4fe)", borderTopWidth: 1, borderTopStyle: "solid", color: "var(--thinking-text, #7e22ce)" }}>
              <MarkdownText>{content}</MarkdownText>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
