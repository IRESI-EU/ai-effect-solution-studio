"use client";

import { ArrowUp, CircleCheck, ChevronDown, Circle, GripVertical, Move, Spline, Sparkles, MousePointerClick } from "lucide-react";
import { useEffect, useRef, useState } from "react";

export type ProposedStep = {
  ref: string;
  service_id: string;
  service_name: string;
  provider: string;
  why: string;
  settings: Record<string, unknown>;
};

export type ProposedWorkflow = {
  steps: ProposedStep[];
  connections: { from_ref: string; to_ref: string }[];
};

type ChatTurn = {
  role: "user" | "assistant";
  content: string;
  workflow?: ProposedWorkflow | null;
  errors?: string[];
  question?: string | null;
  applied?: boolean;
  local?: boolean; // a change made on the canvas from a suggestion, not by the model
};

/** A next step offered under the chat; act() changes the canvas and may return a note for the chat. */
export type AssistantSuggestion = { id: string; label: string; act: () => string | null | void };

type Status = { enabled: boolean; provider: string; model: string; daily_limit: number; used_last_24h: number };

const EXAMPLES = [
  "Generate German grid load and production time series with 2 decimal places",
  "Synthesise a Dutch distribution grid with random seed 7 and high loading, then benchmark control approaches on it",
  "Generate at most 5 district-heating network topologies and draw them",
  "Benchmark control approaches on a low-loading Dutch grid, and separately design district-heating topologies",
];

export function DesignAssistant({
  getCurrent,
  onApply,
  onUndo,
  canUndo,
  suggestions = [],
}: {
  getCurrent: () => { steps: unknown[]; connections: unknown[] } | null;
  onApply: (workflow: ProposedWorkflow) => void;
  onUndo: () => void;
  canUndo: boolean;
  onRun?: () => void;
  onShowSettings?: () => void;
  suggestions?: AssistantSuggestion[];
}) {
  const [status, setStatus] = useState<Status | null>(null);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef<HTMLDivElement>(null);
  const [used, setUsed] = useState<Set<string>>(new Set());
  const [guideOpen, setGuideOpen] = useState(true);

  function runSuggestion(suggestion: AssistantSuggestion) {
    const note = suggestion.act();
    if (note) setTurns((current) => [...current, { role: "user", content: suggestion.label }, { role: "assistant", content: note, local: true }]);
  }

  useEffect(() => {
    fetch("/api/design-ai/status", { credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then(setStatus)
      .catch(() => setStatus(null));
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [turns, busy]);

  async function send(text: string) {
    const content = text.trim();
    if (!content || busy) return;
    const history = [...turns, { role: "user" as const, content }];
    setUsed((current) => new Set(current).add(content));
    setGuideOpen(false);
    setTurns(history);
    setDraft("");
    setError("");
    setBusy(true);
    try {
      const res = await fetch("/api/design-ai/compose", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          messages: history.map((t) => ({ role: t.role, content: t.content })),
          current: getCurrent(),
        }),
      });
      const data = await res.json().catch(() => null);
      if (!res.ok) throw new Error(typeof data?.detail === "string" ? data.detail : `The assistant is unavailable (HTTP ${res.status}).`);
      const replyText: string = data.reply || "";
      const askAgain = data.clarifying_question && !replyText.trim().endsWith("?");
      const reply =
        [replyText, askAgain ? data.clarifying_question : null].filter(Boolean).join("\n\n") ||
        "I could not produce a workflow for that request.";
      const turn: ChatTurn = {
        role: "assistant",
        content: reply,
        workflow: data.workflow,
        errors: data.errors,
        question: data.clarifying_question,
        applied: false,
      };
      if (data.valid && data.workflow) {
        onApply(data.workflow);
        turn.applied = true;
      }
      setTurns([...history, turn]);
      setStatus((s) => (s ? { ...s, used_last_24h: s.used_last_24h + 1 } : s));
    } catch (e) {
      setError(e instanceof Error ? e.message : "The assistant is unavailable.");
      setTurns(history.slice(0, -1));
      setDraft(content);
    } finally {
      setBusy(false);
    }
  }

  const lastTurn = turns.length ? turns[turns.length - 1] : null;

  if (status && !status.enabled) {
    return (
      <div style={{ color: "#667085", lineHeight: 1.6 }}>
        <h3 style={{ marginTop: 0 }}>Design with AI</h3>
        <p>The AI assistant is switched off on this platform. You can still build workflows by dragging services onto the canvas.</p>
      </div>
    );
  }

  return (
    <div className="assistant" aria-label="Design with AI">
      <section className={`assistant-guide${guideOpen ? " is-open" : ""}`}>
        <button type="button" className="assistant-guide__toggle" aria-expanded={guideOpen} onClick={() => setGuideOpen((open) => !open)}>
          How to build a solution <ChevronDown size={16} aria-hidden="true" />
        </button>
        {guideOpen && (
          <div className="assistant-guide__body">
            <h4>Try doing</h4>
            <ul className="assistant-guide__do">
              <li><GripVertical size={15} aria-hidden="true" /> Drag a service from the list onto the canvas</li>
              <li><Move size={15} aria-hidden="true" /> Drag steps to rearrange the workflow</li>
              <li><Spline size={15} aria-hidden="true" /> Drag from a step&apos;s output dot to connect it</li>
              <li><MousePointerClick size={15} aria-hidden="true" /> Right-click a step to replace or remove it</li>
            </ul>
            <h4>Try asking</h4>
            <ul className="assistant-guide__ask">
              {EXAMPLES.map((example) => (
                <li key={example}>
                  <button type="button" onClick={() => send(example)} disabled={busy}>
                    {used.has(example) ? <CircleCheck size={16} className="is-done" aria-hidden="true" /> : <Circle size={16} aria-hidden="true" />}
                    {example}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>

      <div className="assistant-head">
        <span className="assistant-head__avatar" aria-hidden="true"><Sparkles size={18} /></span>
        <div>
          <strong>Assistant</strong>
          <small>
            {status ? `${status.model} · ${Math.max(0, status.daily_limit - status.used_last_24h)} requests left today` : "Builds workflows from the catalogue"}
          </small>
        </div>
      </div>

      <div className="assistant-chat">
        {turns.length === 0 && (
          <div className="assistant-bubble assistant-bubble--ai">
            Hi! Describe the experiment you want to run, and I&apos;ll put together a workflow from the catalogue, using only services that fit together.
          </div>
        )}
        {turns.map((turn, index) => (
          <div key={index} className={`assistant-bubble ${turn.role === "user" ? "assistant-bubble--user" : "assistant-bubble--ai"}`}>
            <div style={{ whiteSpace: "pre-wrap" }}>{turn.content}</div>
            {turn.workflow && turn.workflow.steps.length > 0 && (
              <ol className="assistant-steps">
                {turn.workflow.steps.map((step) => (
                  <li key={step.ref}>
                    <strong>{step.service_name}</strong> <span className="muted">({step.provider})</span>
                    {step.why && <div className="muted">{step.why}</div>}
                    {Object.keys(step.settings || {}).length > 0 && (
                      <div className="assistant-steps__settings">
                        Settings: {Object.entries(step.settings).map(([k, v]) => `${k} = ${JSON.stringify(v)}`).join(", ")}
                      </div>
                    )}
                  </li>
                ))}
              </ol>
            )}
            {turn.errors && turn.errors.length > 0 && (
              <div role="alert" className="assistant-error">
                This proposal still has problems, so it was not placed on the canvas:
                <ul>{turn.errors.map((e) => <li key={e}>{e}</li>)}</ul>
              </div>
            )}
            {turn.applied && <small className="assistant-applied">Placed on the canvas.</small>}
          </div>
        ))}
        {busy && <div className="assistant-bubble assistant-bubble--ai assistant-bubble--busy">Designing your workflow<span>.</span><span>.</span><span>.</span></div>}
        <div ref={endRef} />
      </div>

      {error && <p role="alert" className="assistant-error">{error}</p>}

      {!busy && (lastTurn?.question && !lastTurn.applied || (turns.length > 0 && suggestions.length > 0)) && (
        <div className="assistant-chips" aria-label="Suggested next steps">
          {lastTurn?.question && !lastTurn.applied && (
            <button type="button" className="assistant-chip" onClick={() => send("Yes, go ahead")}>Yes, go ahead</button>
          )}
          {turns.length > 0 && suggestions.map((suggestion) => (
            <button key={suggestion.id} type="button" className="assistant-chip" onClick={() => runSuggestion(suggestion)}>{suggestion.label}</button>
          ))}
        </div>
      )}

      <div className="assistant-input">
        <textarea
          aria-label="Describe your experiment"
          value={draft}
          rows={2}
          placeholder={turns.length ? "Ask for a change, e.g. use 4 decimal places" : "Describe your experiment..."}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send(draft);
            }
          }}
        />
        <button type="button" className="assistant-send" onClick={() => send(draft)} disabled={busy || !draft.trim()} aria-label="Send">
          <ArrowUp size={18} aria-hidden="true" />
        </button>
      </div>
      <div className="assistant-actions">
        {canUndo && <button type="button" onClick={onUndo} disabled={busy}>Undo last AI change</button>}
        {turns.length > 0 && <button type="button" onClick={() => { setTurns([]); setGuideOpen(true); }} disabled={busy}>Start over</button>}
        <span>AI suggestions can be wrong; review before running.</span>
      </div>
    </div>
  );
}

