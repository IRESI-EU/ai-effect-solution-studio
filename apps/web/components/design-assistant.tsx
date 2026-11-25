"use client";

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
};

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
}: {
  getCurrent: () => { steps: unknown[]; connections: unknown[] } | null;
  onApply: (workflow: ProposedWorkflow) => void;
  onUndo: () => void;
  canUndo: boolean;
}) {
  const [status, setStatus] = useState<Status | null>(null);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

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

  if (status && !status.enabled) {
    return (
      <div style={{ color: "#667085", lineHeight: 1.6 }}>
        <h3 style={{ marginTop: 0 }}>Design with AI</h3>
        <p>The AI assistant is switched off on this platform. You can still build workflows by dragging services onto the canvas.</p>
      </div>
    );
  }

  return (
    <div style={{ display: "grid", gap: 10 }} aria-label="Design with AI">
      <div>
        <h3 style={{ margin: 0 }}>Design with AI</h3>
        <p style={{ color: "#667085", fontSize: 13, margin: "4px 0 0" }}>
          Describe what you want to achieve. I&apos;ll build a workflow from the catalogue on the canvas, using only
          services that fit together. You can then adjust, save and run it.
        </p>
      </div>

      {turns.length === 0 && (
        <div style={{ display: "grid", gap: 6 }}>
          <small style={{ color: "#667085", fontWeight: 600 }}>Try for example:</small>
          {EXAMPLES.map((example) => (
            <button key={example} type="button" onClick={() => send(example)} disabled={busy} style={exampleButton}>
              {example}
            </button>
          ))}
        </div>
      )}

      <div style={{ display: "grid", gap: 8, maxHeight: 420, overflowY: "auto" }}>
        {turns.map((turn, index) => (
          <div key={index} style={turn.role === "user" ? userBubble : assistantBubble}>
            <div style={{ whiteSpace: "pre-wrap" }}>{turn.content}</div>
            {turn.workflow && turn.workflow.steps.length > 0 && (
              <ol style={{ margin: "8px 0 0", paddingLeft: 18, fontSize: 13 }}>
                {turn.workflow.steps.map((step) => (
                  <li key={step.ref} style={{ marginBottom: 4 }}>
                    <strong>{step.service_name}</strong> <span style={{ color: "#667085" }}>({step.provider})</span>
                    {step.why && <div style={{ color: "#475467" }}>{step.why}</div>}
                    {Object.keys(step.settings || {}).length > 0 && (
                      <div style={{ color: "#5635ce" }}>
                        Settings: {Object.entries(step.settings).map(([k, v]) => `${k} = ${JSON.stringify(v)}`).join(", ")}
                      </div>
                    )}
                  </li>
                ))}
              </ol>
            )}
            {turn.errors && turn.errors.length > 0 && (
              <div role="alert" style={{ color: "#b42318", fontSize: 13, marginTop: 6 }}>
                This proposal still has problems, so it was not placed on the canvas:
                <ul style={{ margin: "4px 0 0", paddingLeft: 18 }}>
                  {turn.errors.map((e) => <li key={e}>{e}</li>)}
                </ul>
              </div>
            )}
            {turn.applied && <small style={{ color: "#067647" }}>Placed on the canvas.</small>}
          </div>
        ))}
        {busy && <div style={assistantBubble}>Designing your workflow...</div>}
        <div ref={endRef} />
      </div>

      {error && <p role="alert" style={{ color: "#b42318", margin: 0 }}>{error}</p>}

      <textarea
        aria-label="Describe your experiment"
        value={draft}
        rows={3}
        placeholder={turns.length ? "Ask for a change, e.g. use 4 decimal places" : "Describe your experiment"}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            send(draft);
          }
        }}
        style={{ width: "100%", padding: 10, boxSizing: "border-box" }}
      />
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        <button type="button" onClick={() => send(draft)} disabled={busy || !draft.trim()} style={primaryButton}>
          {busy ? "Designing..." : "Send"}
        </button>
        {canUndo && (
          <button type="button" onClick={onUndo} disabled={busy} style={secondaryButton}>
            Undo last AI change
          </button>
        )}
        {turns.length > 0 && (
          <button type="button" onClick={() => setTurns([])} disabled={busy} style={secondaryButton}>
            Start over
          </button>
        )}
      </div>
      {status && (
        <small style={{ color: "#98a2b3" }}>
          {status.used_last_24h}/{status.daily_limit} requests today · model: {status.model}. AI suggestions can be wrong;
          review before running.
        </small>
      )}
    </div>
  );
}

const primaryButton = {
  background: "linear-gradient(135deg, #5b2cf2, #4320ca)", color: "white", padding: "8px 12px",
  borderRadius: 10, border: "none", fontWeight: 700, cursor: "pointer",
} as const;

const secondaryButton = {
  background: "white", color: "#5635ce", padding: "8px 12px",
  borderRadius: 10, border: "1px solid #d1c8f3", fontWeight: 700, cursor: "pointer",
} as const;

const exampleButton = {
  textAlign: "left", background: "#f9f8ff", color: "#3e2a9b", padding: "8px 10px",
  borderRadius: 10, border: "1px solid #e4defb", cursor: "pointer", fontSize: 13,
} as const;

const userBubble = {
  justifySelf: "end", maxWidth: "90%", background: "#5b2cf2", color: "white",
  padding: "8px 12px", borderRadius: "12px 12px 2px 12px", fontSize: 14,
} as const;

const assistantBubble = {
  justifySelf: "start", maxWidth: "95%", background: "#f2f4f7", color: "#101828",
  padding: "8px 12px", borderRadius: "12px 12px 12px 2px", fontSize: 14,
} as const;
