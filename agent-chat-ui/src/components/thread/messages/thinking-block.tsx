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
    <div className="mb-2 overflow-hidden rounded-xl border border-purple-200 bg-purple-50">
      <button
        type="button"
        onClick={() => setIsOpen((o) => !o)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-purple-700 transition-colors hover:bg-purple-100"
      >
        <Brain className="size-4 shrink-0" />
        {isStreaming ? (
          <span className="flex items-center gap-1.5">
            Thinking
            <span className="inline-flex gap-0.5">
              <span
                className="size-1.5 animate-bounce rounded-full bg-purple-500"
                style={{ animationDelay: "0ms" }}
              />
              <span
                className="size-1.5 animate-bounce rounded-full bg-purple-500"
                style={{ animationDelay: "150ms" }}
              />
              <span
                className="size-1.5 animate-bounce rounded-full bg-purple-500"
                style={{ animationDelay: "300ms" }}
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
            <div className="border-t border-purple-200 px-4 py-3 text-sm text-purple-900">
              <MarkdownText>{content}</MarkdownText>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
