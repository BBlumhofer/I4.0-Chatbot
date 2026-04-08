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

  const canSend = useMemo(
    () => input.trim().length > 0 && !isLoading,
    [input, isLoading],
  );

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

  async function onSend() {
    const message = input.trim();
    if (!message || isLoading) return;

    setInput("");
    setError(null);
    appendMessage("user", message);
    setIsLoading(true);

    try {
      const data = await callApi<ChatResponse>("chat", {
        message,
        session_id: sessionId,
      });
      setSessionId(data.session_id);
      appendMessage("assistant", data.response || "");
      setAwaitingConfirmation(Boolean(data.requires_confirmation));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unbekannter Fehler");
    } finally {
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

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-4xl flex-col p-4 md:p-6">
      <header className="mb-4 rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
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
          Diese UI nutzt ausschließlich die FastAPI-Endpunkte `/chat` und
          `/chat/confirm`.
        </p>
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
