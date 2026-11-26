"use client";

/*
 * Optional AI help while adding a service. Nothing is sent until the person
 * presses "Send to AI", and the exact text that will be sent is shown first.
 * The server removes anything that looks like a password or key, and answers
 * are only suggestions: nothing is applied without a click.
 */

import { ArrowRight, MessageCircleQuestion, ShieldCheck, Sparkles, X } from "lucide-react";
import { useEffect, useState } from "react";

type Status = { available: boolean; model: string; left: number };
type Fields = Record<string, string>;

export function useHelperStatus(): Status | null {
  const [status, setStatus] = useState<Status | null>(null);
  useEffect(() => {
    fetch("/api/design-ai/status", { credentials: "include" })
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => {
        if (!data) return;
        setStatus({
          available: Boolean(data.onboarding_helper),
          model: String(data.model || "AI model"),
          left: Math.max(0, Number(data.daily_limit || 0) - Number(data.used_last_24h || 0)),
        });
      })
      .catch(() => setStatus(null));
  }, []);
  return status;
}

async function askHelper(task: "draft" | "explain" | "ask", fields: Fields) {
  const response = await fetch("/api/design-ai/onboarding", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ task, fields }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(typeof data?.detail === "string" ? data.detail : `The helper is unavailable (HTTP ${response.status}).`);
  return data as { result: Record<string, unknown>; removed_secrets: number; model: string };
}

const LABELS: Record<string, string> = {
  name: "Service name", description: "Current description", notes: "README or notes", operations: "Operations",
  interface: "How it is called", check: "Platform check", question: "Your question", details: "Service details",
};

/** The consent box: what will be sent, to which model, and the Send button. */
function SendPreview({ fields, status, busy, onSend, onCancel, sendLabel = "Send to AI" }: {
  fields: Fields; status: Status; busy: boolean; onSend: () => void; onCancel?: () => void; sendLabel?: string;
}) {
  const shown = Object.entries(fields).filter(([, value]) => value.trim());
  return (
    <div className="ai-consent">
      <p className="ai-consent__title"><ShieldCheck size={15} aria-hidden="true" /> This text will be sent to {status.model}:</p>
      <dl className="ai-consent__fields">
        {shown.map(([key, value]) => (
          <div key={key}><dt>{LABELS[key] || key}</dt><dd>{value.length > 400 ? `${value.slice(0, 400)}…` : value}</dd></div>
        ))}
      </dl>
      <p className="ai-consent__note">
        Nothing else is sent, and nothing is saved by the helper. Anything that looks like a password or key is removed first. {status.left} AI requests left today.
      </p>
      <div className="ai-consent__actions">
        {onCancel && <button type="button" className="ae-btn ae-btn--secondary" onClick={onCancel} disabled={busy}>Cancel</button>}
        <button type="button" className="ae-btn ae-btn--primary" onClick={onSend} disabled={busy || shown.length === 0 || status.left === 0}>
          <Sparkles size={15} aria-hidden="true" /> {busy ? "Asking…" : sendLabel}
        </button>
      </div>
    </div>
  );
}

function RemovedNote({ count }: { count: number }) {
  if (!count) return null;
  return <p className="ai-removed"><ShieldCheck size={14} aria-hidden="true" /> {count} item{count === 1 ? " that looked like a secret was" : "s that looked like secrets were"} removed before sending.</p>;
}

/* ------------------------------------------------------------ Describe: draft */

export type DraftSuggestion = { description: string; use_when: string; category: string; keywords: string[]; notes: string };

export function DraftHelper({ status, context, onUse }: {
  status: Status | null;
  context: { name: string; description: string; operations: string; interface: string };
  onUse: (patch: Partial<Pick<DraftSuggestion, "description" | "use_when" | "category">>) => void;
}) {
  const [open, setOpen] = useState(false);
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<{ suggestion: DraftSuggestion; removed: number } | null>(null);
  if (!status?.available) return null;

  const fields: Fields = { name: context.name, description: context.description, notes, operations: context.operations, interface: context.interface };

  async function send() {
    setBusy(true);
    setError("");
    try {
      const data = await askHelper("draft", fields);
      setResult({ suggestion: data.result as unknown as DraftSuggestion, removed: data.removed_secrets });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The helper is unavailable.");
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <button type="button" className="ai-trigger" onClick={() => setOpen(true)}>
        <Sparkles size={15} aria-hidden="true" /> Draft the description with AI
      </button>
    );
  }

  return (
    <section className="ai-panel" aria-label="Draft with AI">
      <header className="ai-panel__head">
        <strong><Sparkles size={16} aria-hidden="true" /> Draft with AI</strong>
        <button type="button" className="ai-close" onClick={() => { setOpen(false); setResult(null); }} aria-label="Close"><X size={16} /></button>
      </header>
      {!result && (
        <>
          <label className="wizard-field">
            <span className="wizard-field__label">Paste your README or a few notes about the service (optional)</span>
            <textarea className="ae-input" rows={5} value={notes} onChange={(event) => setNotes(event.target.value)}
              placeholder="What it does, what data it needs, what it produces, who made it…" />
            <small>Paste only what you are happy to share with the AI service. Leave out credentials and unpublished results.</small>
          </label>
          <SendPreview fields={fields} status={status} busy={busy} onSend={send} onCancel={() => setOpen(false)} />
        </>
      )}
      {error && <p className="wizard-error" role="alert">{error}</p>}
      {result && (
        <div className="ai-result">
          <RemovedNote count={result.removed} />
          <Suggestion label="Description" value={result.suggestion.description} onUse={() => onUse({ description: result.suggestion.description })} />
          <Suggestion label="When to use it" value={result.suggestion.use_when} onUse={() => onUse({ use_when: result.suggestion.use_when })} />
          <Suggestion label="Category" value={result.suggestion.category} onUse={() => onUse({ category: result.suggestion.category })} />
          {result.suggestion.notes && <p className="ai-result__notes"><strong>Worth checking:</strong> {result.suggestion.notes}</p>}
          <div className="ai-consent__actions">
            <button type="button" className="ae-btn ae-btn--secondary" onClick={() => setResult(null)}>Try again</button>
            <button type="button" className="ae-btn ae-btn--primary" onClick={() => {
              onUse({ description: result.suggestion.description, use_when: result.suggestion.use_when, category: result.suggestion.category });
              setOpen(false);
              setResult(null);
            }}>Use all three</button>
          </div>
          <p className="ai-consent__note">These are suggestions. Read them and change anything that is not right before you continue.</p>
        </div>
      )}
    </section>
  );
}

function Suggestion({ label, value, onUse }: { label: string; value: string; onUse: () => void }) {
  if (!value?.trim()) return null;
  return (
    <div className="ai-suggestion">
      <div><span>{label}</span><p>{value}</p></div>
      <button type="button" className="ae-btn ae-btn--secondary" onClick={onUse}>Use</button>
    </div>
  );
}

/* ------------------------------------------------------------ Review: explain */

type Fix = { problem: string; fix: string; step: "describe" | "connect" | "review" | "outside" };

export function ExplainHelper({ status, messages, details, onGo }: {
  status: Status | null; messages: string[]; details: string; onGo: (step: "describe" | "connect") => void;
}) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<{ summary: string; fixes: Fix[]; removed: number } | null>(null);
  if (!status?.available || messages.length === 0) return null;

  const fields: Fields = { check: messages.map((message) => `- ${message}`).join("\n"), details };

  async function send() {
    setBusy(true);
    setError("");
    try {
      const data = await askHelper("explain", fields);
      const answer = data.result as { summary: string; fixes: Fix[] };
      setResult({ summary: answer.summary, fixes: answer.fixes || [], removed: data.removed_secrets });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The helper is unavailable.");
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <button type="button" className="ai-trigger" onClick={() => setOpen(true)}>
        <Sparkles size={15} aria-hidden="true" /> Explain what to fix, with AI
      </button>
    );
  }
  return (
    <section className="ai-panel" aria-label="Explain with AI">
      <header className="ai-panel__head">
        <strong><Sparkles size={16} aria-hidden="true" /> What to fix</strong>
        <button type="button" className="ai-close" onClick={() => { setOpen(false); setResult(null); }} aria-label="Close"><X size={16} /></button>
      </header>
      {!result && <SendPreview fields={fields} status={status} busy={busy} onSend={send} onCancel={() => setOpen(false)} />}
      {error && <p className="wizard-error" role="alert">{error}</p>}
      {result && (
        <div className="ai-result">
          <RemovedNote count={result.removed} />
          {result.summary && <p>{result.summary}</p>}
          <ol className="ai-fixes">
            {result.fixes.map((fix, index) => (
              <li key={index}>
                <strong>{fix.problem}</strong>
                <span>{fix.fix}</span>
                {(fix.step === "describe" || fix.step === "connect") && (
                  <button type="button" className="link-button" onClick={() => onGo(fix.step as "describe" | "connect")}>
                    Go to {fix.step === "describe" ? "Describe" : "Connect"} <ArrowRight size={13} aria-hidden="true" />
                  </button>
                )}
              </li>
            ))}
          </ol>
        </div>
      )}
    </section>
  );
}

/* ------------------------------------------------------------ Any step: ask */

export function AskHelper({ status }: { status: Status | null }) {
  const [question, setQuestion] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [answers, setAnswers] = useState<{ question: string; answer: string }[]>([]);
  if (!status?.available) return null;

  async function send() {
    setBusy(true);
    setError("");
    try {
      const data = await askHelper("ask", { question });
      setAnswers((current) => [...current, { question, answer: String((data.result as { answer?: string }).answer || "") }]);
      setQuestion("");
      setConfirming(false);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The helper is unavailable.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <details className="ai-ask">
      <summary><MessageCircleQuestion size={16} aria-hidden="true" /> Questions about adding a service? Ask the AI helper</summary>
      <div className="ai-ask__body">
        {answers.map((item, index) => (
          <div key={index} className="ai-ask__pair">
            <p className="assistant-bubble assistant-bubble--user">{item.question}</p>
            <p className="assistant-bubble assistant-bubble--ai">{item.answer}</p>
          </div>
        ))}
        <textarea className="ae-input" rows={2} value={question} onChange={(event) => { setQuestion(event.target.value); setConfirming(false); }}
          placeholder="e.g. My service is a Python script that reads a CSV. What do I need?" aria-label="Your question" />
        {!confirming ? (
          <button type="button" className="ae-btn ae-btn--secondary" disabled={!question.trim()} onClick={() => setConfirming(true)}>Next</button>
        ) : (
          <SendPreview fields={{ question }} status={status} busy={busy} onSend={send} onCancel={() => setConfirming(false)} />
        )}
        {error && <p className="wizard-error" role="alert">{error}</p>}
      </div>
    </details>
  );
}
