"use client";

import { useEffect, useRef, useState } from "react";
import ConversationMessage from "./conversation-message";
import { apiErrorMessage } from "../lib/solution-design";

type State = { solution_id: string; expected_updated_at: string; conversation_revision: number; can_undo: boolean; messages: { role: string; content: string }[]; pending: { id: string; base_updated_at: string; changes: Record<string, unknown>[] } | null };
type Config = { enabled: boolean; saved_solution_workspace: boolean; provider_configured: boolean; test_allowance?: { can_request: boolean; message: string } };
async function request(path: string, body?: unknown) {
  const response = await fetch(`/api/design-ai${path}`, { cache: "no-store", ...(body === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  }) });
  const value = await response.json().catch(() => null);
  if (!response.ok) throw new Error(apiErrorMessage(value, `Request failed (${response.status})`));
  return value;
}

export default function SavedSolutionAssistant({ solutionId, savedVersion, disabled, onMutating }: {
  solutionId: string | null; savedVersion: string | null; disabled: boolean; onMutating: (value: boolean) => void;
}) {
  const [config, setConfig] = useState<Config | null>(null);
  const [state, setState] = useState<State | null>(null);
  const [prompt, setPrompt] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const inFlight = useRef(false);
  useEffect(() => {
    let current = true;
    setState(null); setError("");
    request("/config").then(async next => {
      if (!current) return;
      setConfig(next);
      if (next.enabled && next.saved_solution_workspace && solutionId) {
        const value = await request(`/solutions/${encodeURIComponent(solutionId)}`);
        if (current) setState(value);
      }
    }).catch(reason => { if (current) setError(reason.message); });
    return () => { current = false; };
  }, [solutionId, savedVersion]);
  if (!config?.enabled || !config.saved_solution_workspace) return null;
  const blocked = disabled || busy || !state || !solutionId || state.expected_updated_at !== savedVersion;
  const canChat = config.provider_configured && config.test_allowance?.can_request !== false;
  async function action(kind: "chat" | "apply" | "undo" | "dismiss") {
    if (blocked || !state || inFlight.current || (kind === "chat" && (!canChat || !prompt.trim()))) return;
    inFlight.current = true; setBusy(true); setError("");
    const mutating = kind === "apply" || kind === "undo";
    if (mutating) onMutating(true);
    let navigating = false;
    try {
      const next = await request(`/solutions/${encodeURIComponent(solutionId!)}/${kind}`, {
        expected_updated_at: state.expected_updated_at, conversation_revision: state.conversation_revision,
        ...(kind === "chat" ? { message: prompt } : kind === "undo" ? {} : { proposal_id: state.pending?.id }),
      });
      setState(next);
      if (kind === "chat") setPrompt("");
      if (mutating) {
        // Reload the same canonical solution; never replace local unsaved edits.
        window.location.assign(`/builder?solutionId=${encodeURIComponent(solutionId!)}`);
        navigating = true;
        return;
      }
    } catch (reason) { setError(reason instanceof Error ? reason.message : "The assistant request failed"); }
    finally { inFlight.current = false; setBusy(false); if (mutating && !navigating) onMutating(false); }
  }
  return <section className="card" aria-label="Saved solution assistant" style={{ padding: 20, marginBlock: 20 }}>
    <h2>Design with AI</h2>
    <p>Describe your goal or ask about services. Review proposed changes, then apply and save them to this solution. Use Builder’s deployment controls to run it.</p>
    {!solutionId ? <p>Save a solution to start its conversation.</p> : disabled ? <p role="status">Save your Builder changes and finish the current action before using chat.</p> : null}
    {!canChat && <p role="status">{config.test_allowance?.can_request === false ? config.test_allowance.message : "AI is not connected. Manual Builder editing remains available."}</p>}
    {error && <p role="alert">{error}</p>}
    <div aria-label="Solution conversation" aria-live="polite" style={{ maxHeight: 380, overflowY: "auto" }}>
      {state?.messages.map((message, index) => <article key={index}><strong>{message.role === "user" ? "You" : "Assistant"}</strong><ConversationMessage content={message.content} /></article>)}
    </div>
    {state?.pending && <section aria-label="Review proposed solution changes">
      <h3>Proposed changes</h3>
      <ul>{state.pending.changes.map((change, index) => <li key={index}>
        <strong>{String(change.action).replaceAll("_", " ")}</strong>{change.step ? ` · ${String(change.step)}` : ""}
        <dl>{Object.entries(change).filter(([key]) => !["action", "step"].includes(key)).map(([key, value]) => <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{typeof value === "string" ? value : JSON.stringify(value, null, 2)}</dd></div>)}</dl>
      </li>)}</ul>
      {state.pending.base_updated_at !== state.expected_updated_at && <p role="alert">This proposal predates the current Builder version. Request a new proposal.</p>}
      <button type="button" disabled={blocked || state.pending.base_updated_at !== state.expected_updated_at} onClick={() => action("apply")}>Apply and save reviewed changes</button>{" "}
      <button type="button" disabled={blocked} onClick={() => action("dismiss")}>Dismiss proposal</button>
    </section>}
    <form onSubmit={event => { event.preventDefault(); void action("chat"); }}>
      <label style={{ display: "grid", gap: 8, marginBlock: 12 }}>Your goal or question<textarea value={prompt} onChange={event => setPrompt(event.target.value)} maxLength={4000} rows={3} disabled={blocked || !canChat} /></label>
      <button disabled={blocked || !canChat || !prompt.trim()}>Send message</button>{" "}
      <button type="button" disabled={blocked || !state?.can_undo} onClick={() => action("undo")}>Undo last applied changes</button>
    </form>
    {busy && <p role="status">{inFlight.current ? "Processing your request…" : "Loading…"}</p>}
  </section>;
}
