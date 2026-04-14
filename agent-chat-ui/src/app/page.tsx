"use client";

import Image from "next/image";
import React, { useMemo, useState } from "react";
import LennyPng from "@/components/icons/lenny_laster.png";

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
};

export default function DemoPage(): React.ReactNode {
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [awaitingConfirmation, setAwaitingConfirmation] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [liveStatuses, setLiveStatuses] = useState<string[]>([]);

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

  function appendToMessage(messageId: string, delta: string) {
    setMessages((prev) =>
      prev.map((m) =>
        m.id === messageId
          ? {
              ...m,
              text: `${m.text}${delta}`,
            }
          : m,
      ),
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
              appendToMessage(assistantMessageId, parsed.delta);
            } else if (evt.event === "confirmation" && parsed.message) {
              appendToMessage(assistantMessageId, parsed.message);
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
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMessageId
              ? {
                  ...m,
                  text: data.response,
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
    <main className="mx-auto flex min-h-screen w-full max-w-4xl flex-col p-4 md:p-6">
      <header className="mb-4 rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
        <div className="flex items-start justify-between gap-3">
          <div>
            <Image
              src={LennyPng}
              alt="Lenny der Laster"
              width={140}
              height={60}
              className="mb-2 h-12 w-auto"
              priority
            />
            <h1 className="text-xl font-semibold">I4.0 Chatbot</h1>
            <p className="mt-1 text-sm text-zinc-600">
              Diese UI nutzt die FastAPI-Endpunkte `/chat/stream` und `/chat/confirm`.
            </p>
          </div>

          <button
            type="button"
            onClick={() => void onNewChat()}
            disabled={isLoading}
            className="rounded-lg border border-zinc-300 bg-white px-3 py-1.5 text-sm text-zinc-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Neuer Chat
          </button>
        </div>
      </header>

      <section className="mb-4 flex-1 overflow-y-auto rounded-2xl border border-zinc-200 bg-zinc-50 p-4">
        {messages.length === 0 ? (
          <p className="text-sm text-zinc-500">Stelle eine Frage, um zu starten.</p>
        ) : (
          <div className="space-y-3">
            {messages.map((m) => (
              <article
                key={m.id}
                className={
                  m.role === "user"
                    ? "ml-auto max-w-[85%] rounded-2xl bg-zinc-900 px-4 py-3 text-white"
                    : "mr-auto max-w-[85%] rounded-2xl bg-white px-4 py-3 text-zinc-900 shadow-sm"
                }
              >
                <p className="whitespace-pre-wrap text-sm">{m.text}</p>
              </article>
            ))}
          </div>
        )}
      </section>

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
        <div className="mb-3 rounded-xl border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900">
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

      <form
        onSubmit={(e) => {
          e.preventDefault();
          void onSend();
        }}
        className="flex items-end gap-2"
      >
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleInputKeyDown}
          placeholder="Nachricht eingeben..."
          rows={3}
          className="min-h-[52px] w-full resize-y rounded-xl border border-zinc-300 bg-white p-3 text-sm outline-none ring-zinc-400 focus:ring"
        />
        <button
          type="submit"
          disabled={!canSend}
          className="h-[52px] rounded-xl bg-zinc-900 px-5 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isLoading ? "Sende..." : "Senden"}
        </button>
      </form>
    </main>
  );
}
