"use client";

import Image from "next/image";
import React, { useMemo, useState, useRef, useEffect } from "react";
import LennyPng from "@/components/icons/lenny_laster.png";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ChevronDown, ChevronUp, Brain, SquarePen, LoaderCircle } from "lucide-react";

type ChatResponse = {
  session_id: string;
  response: string;
  requires_confirmation: boolean;
  confirmation_message?: string | null;
};

type StreamFinalEvent = ChatResponse & {
  intent?: string | null;
  capability?: string | null;
  submodel?: string | null;
};

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  thinking?: string;
  isThinkingStreaming?: boolean;
};

/** Extracts <think>…</think> content from a string. */
function extractThinkingAndText(content: string): {
  thinking: string | null;
  isThinkingStreaming: boolean;
  text: string;
} {
  const completeMatch = content.match(/^<think>([\s\S]*?)<\/think>\s*/);
  if (completeMatch) {
    return {
      thinking: completeMatch[1].trim(),
      isThinkingStreaming: false,
      text: content.slice(completeMatch[0].length),
    };
  }
  const openMatch = content.match(/^<think>([\s\S]*)$/);
  if (openMatch) {
    return { thinking: openMatch[1], isThinkingStreaming: true, text: "" };
  }
  return { thinking: null, isThinkingStreaming: false, text: content };
}

function ThinkingBlock({
  content,
  isStreaming,
}: {
  content: string;
  isStreaming?: boolean;
}) {
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
              <span className="size-1.5 animate-bounce rounded-full bg-purple-500" style={{ animationDelay: "0ms" }} />
              <span className="size-1.5 animate-bounce rounded-full bg-purple-500" style={{ animationDelay: "150ms" }} />
              <span className="size-1.5 animate-bounce rounded-full bg-purple-500" style={{ animationDelay: "300ms" }} />
            </span>
          </span>
        ) : (
          <span>Thought for a moment</span>
        )}
        <span className="ml-auto">
          {isOpen ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
        </span>
      </button>
      {isOpen && (
        <div className="border-t border-purple-200 px-4 py-3 text-sm text-purple-900 whitespace-pre-wrap">
          {content}
        </div>
      )}
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.role === "user") {
    return (
      <article className="ml-auto max-w-[85%] rounded-2xl bg-zinc-900 px-4 py-3 text-white">
        <p className="whitespace-pre-wrap text-sm">{message.text}</p>
      </article>
    );
  }

  const { thinking, isThinkingStreaming, text: visibleText } = extractThinkingAndText(
    message.text,
  );
  // Also respect pre-extracted thinking from streaming
  const finalThinking = message.thinking !== undefined ? message.thinking : thinking;
  const finalIsStreaming = message.isThinkingStreaming !== undefined ? message.isThinkingStreaming : isThinkingStreaming;
  const finalText = message.thinking !== undefined ? message.text : visibleText;

  return (
    <article className="mr-auto max-w-[85%]">
      {finalThinking !== null && finalThinking !== undefined && (
        <ThinkingBlock content={finalThinking} isStreaming={finalIsStreaming} />
      )}
      {finalText && (
        <div className="rounded-2xl bg-white px-4 py-3 text-zinc-900 shadow-sm">
          <div className="prose prose-sm max-w-none text-sm">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{finalText}</ReactMarkdown>
          </div>
        </div>
      )}
    </article>
  );
}

export default function DemoPage(): React.ReactNode {
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [awaitingConfirmation, setAwaitingConfirmation] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [liveStatuses, setLiveStatuses] = useState<string[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, liveStatuses]);

  const canSend = useMemo(
    () => input.trim().length > 0 && !isLoading,
    [input, isLoading],
  );

  function handleInputKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    const isComposing = Boolean((event.nativeEvent as { isComposing?: boolean }).isComposing);
    if (isComposing) return;
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void onSend();
    }
  }

  async function callApi<T>(path: string, payload: unknown): Promise<T> {
    const res = await fetch(`/api/${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || `HTTP ${res.status}`);
    }

    return (await res.json()) as T;
  }

  function appendMessage(role: ChatMessage["role"], text: string) {
    setMessages((prev) => [
      ...prev,
      { id: `${Date.now()}-${Math.random()}`, role, text },
    ]);
  }

  function createAssistantPlaceholder(): string {
    const id = `${Date.now()}-${Math.random()}`;
    setMessages((prev) => [...prev, { id, role: "assistant", text: "" }]);
    return id;
  }

  /** Update streaming message, extracting thinking on the fly */
  function updateStreamingMessage(messageId: string, fullText: string) {
    setMessages((prev) =>
      prev.map((m) => {
        if (m.id !== messageId) return m;
        const { thinking, isThinkingStreaming, text } = extractThinkingAndText(fullText);
        return {
          ...m,
          text: thinking !== null ? text : fullText,
          thinking: thinking !== null ? thinking : undefined,
          isThinkingStreaming: thinking !== null ? isThinkingStreaming : undefined,
        };
      }),
    );
  }

  function pushStatus(status: string) {
    setLiveStatuses((prev) => {
      if (prev[prev.length - 1] === status) {
        return prev;
      }
      const next = [...prev, status];
      return next.slice(-8);
    });
  }

  function statusIcon(status: string): string {
    const s = status.toLowerCase();
    if (s.includes("neo4j")) return "🕸";
    if (s.includes("rag") || s.includes("search_docs")) return "📚";
    if (s.includes("opc")) return "📡";
    if (s.includes("kafka")) return "🛰";
    if (s.includes("tool geplant") || s.includes("fuehre") || s.includes("führe")) return "🛠";
    if (s.includes("asset aufgeloest") || s.includes("asset aufgelöst")) return "🏷";
    if (s.includes("route") || s.includes("waehle") || s.includes("wähle")) return "🧭";
    if (s.includes("denke")) return "🧠";
    if (s.includes("ergebnis")) return "✅";
    if (s.includes("analysiere")) return "🧠";
    if (s.includes("empfange")) return "💬";
    if (s.includes("formuliere")) return "✍";
    return "•";
  }

  function parseSseChunk(chunk: string): Array<{ event: string; data: string }> {
    const events: Array<{ event: string; data: string }> = [];
    const blocks = chunk.split(/\r?\n\r?\n/);
    for (const block of blocks) {
      const lines = block.split(/\r?\n/).filter(Boolean);
      if (lines.length === 0) continue;
      let event = "message";
      const dataLines: string[] = [];
      for (const line of lines) {
        if (line.startsWith("event:")) {
          event = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          dataLines.push(line.slice(5).trim());
        }
      }
      events.push({ event, data: dataLines.join("\n") });
    }
    return events;
  }

  async function streamChat(message: string, assistantMessageId: string): Promise<StreamFinalEvent> {
    const res = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, session_id: sessionId }),
    });

    if (!res.ok || !res.body) {
      const text = await res.text();
      throw new Error(text || `HTTP ${res.status}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let finalEvent: StreamFinalEvent | null = null;
    let accumulatedText = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const parts = buffer.split(/\r?\n\r?\n/);
      buffer = parts.pop() ?? "";

      for (const raw of parts) {
        for (const evt of parseSseChunk(raw)) {
          if (!evt.data) continue;
          try {
            const parsed = JSON.parse(evt.data) as {
              message?: string;
              delta?: string;
            } & Partial<StreamFinalEvent>;
            if (evt.event === "status" && parsed.message) {
              pushStatus(parsed.message);
            } else if (evt.event === "chunk" && parsed.delta) {
              accumulatedText += parsed.delta;
              updateStreamingMessage(assistantMessageId, accumulatedText);
            } else if (evt.event === "confirmation" && parsed.message) {
              accumulatedText += parsed.message;
              updateStreamingMessage(assistantMessageId, accumulatedText);
            } else if (evt.event === "final") {
              finalEvent = parsed as StreamFinalEvent;
            } else if (evt.event === "error") {
              throw new Error(parsed.message || "Streaming-Fehler");
            }
          } catch (error) {
            throw error instanceof Error ? error : new Error("Fehler beim Verarbeiten des Streams");
          }
        }
      }
    }

    if (!finalEvent) {
      throw new Error("Stream endete ohne finales Ergebnis");
    }

    return finalEvent;
  }

  async function onSend() {
    const message = input.trim();
    if (!message || isLoading) return;

    setInput("");
    setError(null);
    setLiveStatuses([]);
    appendMessage("user", message);
    const assistantMessageId = createAssistantPlaceholder();
    setIsLoading(true);

    try {
      const data = await streamChat(message, assistantMessageId);
      setSessionId(data.session_id);
      if (data.response) {
        const { thinking, isThinkingStreaming, text } = extractThinkingAndText(data.response);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMessageId
              ? {
                  ...m,
                  text: thinking !== null ? text : data.response,
                  thinking: thinking !== null ? thinking : undefined,
                  isThinkingStreaming: thinking !== null ? isThinkingStreaming : undefined,
                }
              : m,
          ),
        );
      }
      setAwaitingConfirmation(Boolean(data.requires_confirmation));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unbekannter Fehler");
    } finally {
      setLiveStatuses([]);
      setIsLoading(false);
    }
  }

  async function onConfirm(confirmed: boolean) {
    if (!sessionId || isLoading) return;

    setError(null);
    setIsLoading(true);
    try {
      const data = await callApi<ChatResponse>("chat/confirm", {
        session_id: sessionId,
        confirmed,
      });
      appendMessage("assistant", data.response || "");
      setAwaitingConfirmation(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unbekannter Fehler");
    } finally {
      setIsLoading(false);
    }
  }

  async function onNewChat() {
    if (isLoading) return;

    setError(null);

    if (sessionId) {
      try {
        const res = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}`, {
          method: "DELETE",
        });
        if (!res.ok) {
          const text = await res.text();
          throw new Error(text || `HTTP ${res.status}`);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Session konnte nicht geloescht werden");
        return;
      }
    }

    setSessionId(null);
    setMessages([]);
    setAwaitingConfirmation(false);
    setLiveStatuses([]);
    setInput("");
  }

  return (
    <div className="flex h-screen w-full flex-col overflow-hidden">
      {/* Top navigation */}
      <header className="flex h-14 shrink-0 items-center justify-between border-b bg-white px-4 shadow-sm" style={{ borderColor: "#32b9b4" }}>
        <div className="flex items-center gap-2">
          <Image
            src={LennyPng}
            alt="Lenny der Laster"
            width={140}
            height={60}
            className="h-9 w-auto"
            priority
          />
          <span className="hidden text-lg font-semibold sm:block" style={{ color: "#1b567c" }}>
            I4.0 Chatbot
          </span>
        </div>
        <button
          type="button"
          onClick={() => void onNewChat()}
          disabled={isLoading}
          className="flex items-center gap-2 rounded-lg border border-zinc-300 bg-white px-3 py-1.5 text-sm text-zinc-800 disabled:cursor-not-allowed disabled:opacity-50 hover:bg-zinc-50"
        >
          <SquarePen className="size-4" />
          <span className="hidden sm:inline">Neuer Chat</span>
        </button>
      </header>

      {/* Messages area */}
      <section className="flex-1 overflow-y-auto bg-zinc-50 px-4 py-4">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
            <Image src={LennyPng} alt="Lenny der Laster" width={120} height={60} className="h-20 w-auto" />
            <p className="text-xl font-semibold" style={{ color: "#1b567c" }}>Wie kann ich helfen?</p>
            <p className="text-sm text-zinc-500">Stelle eine Frage, um zu starten.</p>
          </div>
        ) : (
          <div className="mx-auto max-w-3xl space-y-4">
            {messages.map((m) => (
              <MessageBubble key={m.id} message={m} />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </section>

      {/* Status / error banners */}
      <div className="mx-auto w-full max-w-3xl px-4">
        {error ? (
          <div className="mb-3 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        ) : null}

        {isLoading && liveStatuses.length > 0 ? (
          <div className="mb-3 flex flex-wrap items-center gap-2 rounded-xl border border-blue-200 bg-blue-50 p-3">
            <span className="mr-2 text-sm font-medium text-blue-900">Live:</span>
            {liveStatuses.map((status, idx) => (
              <span
                key={`${status}-${idx}`}
                className="rounded-full border border-blue-300 bg-white px-2.5 py-1 text-xs text-blue-900"
              >
                {statusIcon(status)} {status}
              </span>
            ))}
          </div>
        ) : null}

        {isLoading && liveStatuses.length === 0 ? (
          <div className="mb-3 flex items-center gap-2 rounded-xl border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900">
            <LoaderCircle className="size-4 animate-spin" />
            Antwort wird vorbereitet ...
          </div>
        ) : null}

        {awaitingConfirmation ? (
          <div className="mb-3 flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3">
            <p className="mr-auto text-sm text-amber-900">Bestätigung erforderlich.</p>
            <button
              type="button"
              onClick={() => onConfirm(false)}
              disabled={isLoading}
              className="rounded-lg border border-zinc-300 bg-white px-3 py-1.5 text-sm disabled:opacity-50"
            >
              Abbrechen
            </button>
            <button
              type="button"
              onClick={() => onConfirm(true)}
              disabled={isLoading}
              className="rounded-lg bg-zinc-900 px-3 py-1.5 text-sm text-white disabled:opacity-50"
            >
              Bestätigen
            </button>
          </div>
        ) : null}
      </div>

      {/* Input form */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void onSend();
        }}
        className="mx-auto w-full max-w-3xl px-4 pb-4"
      >
        <div className="flex items-end gap-2 rounded-2xl border border-zinc-300 bg-white p-2 shadow-sm">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleInputKeyDown}
            placeholder="Nachricht eingeben..."
            rows={1}
            className="min-h-[44px] flex-1 resize-none bg-transparent p-2 text-sm outline-none"
          />
          <button
            type="submit"
            disabled={!canSend}
            className="h-10 rounded-xl px-4 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
            style={{ backgroundColor: "#1b567c" }}
          >
            {isLoading ? <LoaderCircle className="size-4 animate-spin" /> : "Senden"}
          </button>
        </div>
      </form>
    </div>
  );
}
