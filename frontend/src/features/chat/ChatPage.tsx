import { FormEvent, useState } from "react";

import { Alert } from "@/components/ui/Alert";
import { sendChatMessage, type ChatCitation } from "@/lib/api/chat";

interface ChatTurn {
  id: string;
  role: "user" | "assistant";
  content: string;
  notice?: string | null;
  citations?: ChatCitation[];
}

export function ChatPage() {
  const [conversationId, setConversationId] = useState<string>();
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const question = draft.trim();
    if (!question || busy) return;
    setDraft("");
    setError(null);
    setBusy(true);
    setTurns((current) => [
      ...current,
      { id: crypto.randomUUID(), role: "user", content: question },
    ]);

    try {
      const response = await sendChatMessage(question, conversationId);
      setConversationId(response.conversation_id);
      setTurns((current) => [
        ...current,
        {
          id: response.assistant_message_id,
          role: "assistant",
          content: response.answer,
          notice: response.notice,
          citations: response.citations,
        },
      ]);
    } catch {
      setError("No se pudo completar la respuesta. Revisa Ollama y vuelve a intentarlo.");
    } finally {
      setBusy(false);
    }
  }

  function startNewConversation() {
    setConversationId(undefined);
    setTurns([]);
    setError(null);
  }

  return (
    <div className="mx-auto flex min-h-[calc(100vh-12rem)] max-w-4xl flex-col gap-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Chat con el agente</h1>
          <p className="mt-1 text-sm text-slate-600">
            Ollama responde localmente y cita los fragmentos de documentos procesados que use.
          </p>
        </div>
        <button
          type="button"
          onClick={startNewConversation}
          className="shrink-0 rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Nueva conversación
        </button>
      </div>

      <Alert variant="info">
        Si aún no hay documentos procesados, puedes conversar de forma general; el chat indicará que la respuesta no está respaldada por documentos.
      </Alert>
      {error ? <Alert variant="error">{error}</Alert> : null}

      <section
        aria-live="polite"
        className="flex-1 space-y-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6"
      >
        {turns.length === 0 ? (
          <p className="py-12 text-center text-sm text-slate-500">
            Pregunta algo sobre tus documentos o inicia una conversación general.
          </p>
        ) : (
          turns.map((turn) => (
            <article
              key={turn.id}
              className={`max-w-[90%] rounded-xl px-4 py-3 ${
                turn.role === "user"
                  ? "ml-auto bg-slate-900 text-white"
                  : "mr-auto bg-slate-100 text-slate-900"
              }`}
            >
              <p className="whitespace-pre-wrap text-sm leading-6">{turn.content}</p>
              {turn.notice ? (
                <p className="mt-3 border-t border-slate-300 pt-2 text-xs text-amber-800">
                  {turn.notice}
                </p>
              ) : null}
              {turn.citations?.length ? (
                <div className="mt-3 space-y-2 border-t border-slate-300 pt-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">
                    Fuentes consultadas
                  </p>
                  {turn.citations.map((citation) => (
                    <div key={`${turn.id}-${citation.order}`} className="rounded-md bg-white p-3 text-slate-800">
                      <p className="text-xs font-semibold">
                        [{citation.order}] {citation.document_title}
                        {citation.page_number ? ` · Página ${citation.page_number}` : ""}
                        {citation.location ? ` · ${citation.location}` : ""}
                      </p>
                      <p className="mt-1 text-xs leading-5 text-slate-600">{citation.excerpt}</p>
                    </div>
                  ))}
                </div>
              ) : null}
            </article>
          ))
        )}
        {busy ? <p className="text-sm text-slate-500">El agente está pensando…</p> : null}
      </section>

      <form onSubmit={(event) => void handleSubmit(event)} className="flex gap-3">
        <label htmlFor="chat-message" className="sr-only">
          Escribe tu pregunta
        </label>
        <textarea
          id="chat-message"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              event.currentTarget.form?.requestSubmit();
            }
          }}
          maxLength={6000}
          rows={2}
          placeholder="Escribe tu pregunta…"
          className="min-w-0 flex-1 resize-y rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
        />
        <button
          type="submit"
          disabled={!draft.trim() || busy}
          className="self-end rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Enviar
        </button>
      </form>
    </div>
  );
}
