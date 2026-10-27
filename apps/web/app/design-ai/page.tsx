"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { Background, Controls, ReactFlow, type Edge, type Node, Position } from "@xyflow/react";
import { ArrowRight, Check, ChevronDown, LoaderCircle, MessageSquare, Save, Send, Sparkles, Undo2, X } from "lucide-react";
import "@xyflow/react/dist/style.css";
import { useAuth } from "../../components/auth-context";
import { apiErrorMessage } from "../../lib/solution-design";
import { allowanceFromError, startingPrompts, type TestAllowance } from "./allowance";
import "./workspace.css";

type Validation = { valid: boolean; errors: string[]; unknown: string[]; contracts?: {node_id: string; resolution: string; version: string | null}[]; required_inputs: { operation: string; name: string; resolution: string }[] };
type Design = { name: string; description: string; nodes: Node[]; edges: Edge[]; run_input: Record<string, unknown> | null; input_policy: { evidence_reference: string; json_schema: Record<string, unknown> } | null };
type Draft = { id: string; revision: number; template_key: string; design: Design; validation: Validation; dirty: boolean; saved_solution_id: string | null; can_undo: boolean; reference_note: string; source: { revision: string }; pending: { id: string; design: Design; turn: { edits: { kind: string; value: string; node_id: string | null }[] }; validation: Validation } | null };
type Template = { key: string; label: string; description?: string; available: boolean; reason?: string; operations?: string[] };
type Message = { role: "user" | "assistant"; content: string };
type Activity = { tool: string; status: string; summary: string };
type CatalogueService = { id: string; name: string; description: string; operation_name: string; status: string; version: string };

class DesignError extends Error {
  constructor(message: string, readonly activity: Activity[] = [], readonly allowance: TestAllowance | null = null) { super(message); }
}

async function api(path: string, body?: unknown, signal?: AbortSignal) {
  const response = await fetch(`/api/design-ai${path}`, { method: body === undefined ? "GET" : "POST", cache: "no-store", signal,
    ...(body === undefined ? {} : { headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }) });
  const value = await response.json().catch(() => null);
  if (!response.ok) throw new DesignError(apiErrorMessage(value, `The request failed (HTTP ${response.status}).`), value?.detail?.activity || [], allowanceFromError(value));
  return value;
}

function layout(design: Design): Node[] {
  const remaining = new Set(design.nodes.map((node) => node.id));
  const ordered: string[] = [];
  while (remaining.size) {
    const next = [...remaining].find((id) => !design.edges.some((edge) => edge.target === id && remaining.has(edge.source)));
    if (!next) break;
    ordered.push(next); remaining.delete(next);
  }
  return design.nodes.map((node) => {
    const service = node.data?.service as CatalogueService | undefined;
    return { ...node, position: { x: 80, y: Math.max(ordered.indexOf(node.id), 0) * 125 }, sourcePosition: Position.Bottom, targetPosition: Position.Top,
      data: { ...node.data, label: <div className="ai-graph-label"><span>{String(node.data?.label || service?.name || node.id)}</span>{service && <small>{service.operation_name}</small>}</div> },
      style: { width: 245, borderRadius: 12, border: `1px solid ${service ? "#c9bbfb" : "#dedde9"}`, background: service ? "#f6f3ff" : "white", color: "#24204c", padding: 13 } };
  });
}

export default function DesignAIPage() {
  const { user } = useAuth();
  const [config, setConfig] = useState<{ enabled: boolean; provider_configured: boolean; provider_name?: string; provider_mode?: string; model?: string | null; test_allowance?: TestAllowance } | null>(null);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [activity, setActivity] = useState<Activity[]>([]);
  const [prompt, setPrompt] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [retryPrompt, setRetryPrompt] = useState("");
  const [recommendation, setRecommendation] = useState<string | null>(null);
  const [showProposed, setShowProposed] = useState(true);
  const controller = useRef<AbortController | null>(null);
  const inFlight = useRef(false);
  const chatEnd = useRef<HTMLDivElement | null>(null);
  const storageKey = user ? `design-ai-draft:${user.id}` : null;
  const allowance = config?.test_allowance;
  const allowancePaused = !!allowance && !allowance.can_request;
  const chatEnabled = !!config?.provider_configured && !allowancePaused;

  async function refreshAllowance() {
    try { setConfig(await api("/config")); }
    catch { /* Keep the last known allowance state; the server still enforces it. */ }
  }

  async function initialize() {
    setError("");
    try {
      const value = await api("/config"); setConfig(value);
      if (value.enabled) {
        setTemplates(await api("/templates"));
        const previous = storageKey ? localStorage.getItem(storageKey) : null;
        if (previous) {
          try { setDraft(await api(`/drafts/${encodeURIComponent(previous)}`)); }
          catch (failure) { localStorage.removeItem(storageKey!); throw failure; }
        }
      }
    } catch (failure) { setError(failure instanceof Error ? failure.message : "The workspace could not be loaded."); }
  }
  useEffect(() => { if (user) void initialize(); return () => controller.current?.abort(); }, [user?.id]);
  useEffect(() => { if (storageKey && draft) localStorage.setItem(storageKey, draft.id); }, [draft, storageKey]);
  useEffect(() => { const history = chatEnd.current?.parentElement; if (history) history.scrollTop = history.scrollHeight; }, [messages, busy]);

  async function action(label: string, operation: () => Promise<void>) {
    if (inFlight.current) return;
    inFlight.current = true; setBusy(label); setError("");
    try { await operation(); }
    catch (failure) {
      setError(failure instanceof DesignError && failure.allowance ? "" : failure instanceof Error ? failure.message : "The request could not be completed.");
      if (failure instanceof DesignError) {
        setActivity((current) => [...current, ...failure.activity].slice(-60));
        if (failure.allowance) { setConfig((current) => current ? { ...current, test_allowance: failure.allowance! } : current); setRetryPrompt(""); }
      }
    }
    finally { inFlight.current = false; setBusy(null); }
  }

  async function start(key: string) {
    await action("Creating copy", async () => {
      const value = await api("/drafts", { template_key: key }); setDraft(value); setShowProposed(true); setRecommendation(null);
      setMessages([{ role: "assistant", content: `I created a separate editable copy of ${templates.find((item) => item.key === key)?.label || key}. You can ask me to explain the workflow, rename your draft, or change a service's display label. ${value.design.input_policy ? "Verified run inputs are also available." : "Domain input editing is awaiting verified wrapper metadata."}` }]);
    });
  }

  async function send(text = prompt, retry = false) {
    if (!text.trim() || inFlight.current || !chatEnabled) return;
    const before = messages;
    if (!retry) setMessages((current) => [...current, { role: "user", content: text }]);
    setPrompt(""); setRetryPrompt("");
    await action("Thinking", async () => {
      const abort = new AbortController(); controller.current = abort;
      try {
        const value = await api("/chat", { message: text, draft_id: draft?.id || null, revision: draft?.revision ?? null,
          history: before.slice(-6).map((message) => ({ ...message, content: message.content.slice(0, 2000) })) }, abort.signal);
        setMessages((current) => [...current, { role: "assistant", content: value.message }]);
        setActivity((current) => [...current, ...value.activity].slice(-60));
        if (value.draft) { setDraft(value.draft); setShowProposed(true); }
        if (value.recommendation) setRecommendation(value.recommendation.key);
      } catch (failure) {
        if (abort.signal.aborted) {
          setMessages((current) => [...current, { role: "assistant", content: "Request cancelled. No changes have been applied." }]);
          if (draft) setDraft(await api(`/drafts/${draft.id}`));
        } else { setRetryPrompt(failure instanceof DesignError && failure.allowance ? "" : text); throw failure; }
      } finally { controller.current = null; await refreshAllowance(); }
    });
  }

  const preview = draft?.pending && showProposed ? draft.pending.design : draft?.design;
  const nodes = useMemo(() => preview ? layout(preview) : [], [preview]);
  const services = (draft?.design.nodes || []).flatMap((node) => node.data?.service ? [{ node, service: node.data.service as CatalogueService }] : []);

  if (!config) return <div className="ai-page"><h1>Design with AI</h1>{error ? <div role="alert">{error} <button onClick={initialize}>Retry</button></div> : <p>Loading design workspace…</p>}</div>;
  if (!config.enabled) return <div className="ai-page"><h1>Design with AI</h1><div className="card ai-disabled"><Sparkles /><h2>The AI design pilot is not enabled</h2><p>Your administrator can enable it in a private development or staging environment.</p><Link href="/builder">Open Build Solution <ArrowRight size={15} /></Link></div></div>;

  return <div className="ai-page">
    <div className="ai-heading"><div><div className="ai-eyebrow"><Sparkles size={15} /> SOLUTION STUDIO <span>PILOT</span></div><h1>Design with AI</h1><p>Start with an existing workflow. Make it your own.</p></div><Link href="/builder">Build Solution <ArrowRight size={16} /></Link></div>
    {error && <div className="ai-alert" role="alert">{error} <button onClick={() => draft ? action("Refreshing", async () => setDraft(await api(`/drafts/${draft.id}`))) : initialize()}>Refresh</button>{retryPrompt && <button disabled={!!busy || !chatEnabled} onClick={() => send(retryPrompt, true)}>Retry request</button>}</div>}
    {!config.provider_configured && <div className="ai-config-notice" role="status"><Sparkles size={17} /><div><strong>AI provider not configured</strong><span>You can explore configured templates, create a copy and save it. Conversation needs a server-side provider connection.</span></div></div>}
    {allowance && <div className="ai-config-notice" role="status" data-testid="test-allowance"><Sparkles size={17} /><div><strong>{allowancePaused ? "AI testing paused" : "Local AI test allowance"}</strong><span>{allowance.message}</span>{allowance.remaining_calls !== undefined && <span>{allowance.remaining_calls} provider calls remaining · US${allowance.remaining_usd?.toFixed(5)} remaining · maximum reservation US${allowance.next_reservation_usd?.toFixed(3)} per request.</span>}</div><button disabled={!!busy} onClick={() => void refreshAllowance()}>Check allowance</button></div>}
    <div className="ai-workspace">
      <aside className="ai-panel ai-library"><div className="ai-panel-title"><span>Design library</span><span className="ai-count">{templates.filter((item) => item.available).length}</span></div>
        <p className="ai-panel-intro">Existing solutions, selected for this pilot.</p>
        <div className="ai-templates">{templates.map((item) => <button key={item.key} className={`ai-template ${draft?.template_key === item.key ? "selected" : ""}`} disabled={!item.available || !!busy} title={item.reason} onClick={() => start(item.key)}>
          <span className="ai-template-name">{item.label}{draft?.template_key === item.key && <Check size={15} />}</span><small>{item.available ? `${item.operations?.length} services · Create a copy` : item.reason}</small>
        </button>)}</div>
        {draft && <><div className="ai-panel-title ai-service-heading">Services in this design <span className="ai-count">{services.length}</span></div>{services.map(({ node, service }, index) => <article className="ai-service" key={node.id}><div className="ai-service-top"><span>{String(index + 1).padStart(2, "0")}</span><strong>{service.name}</strong></div><p>{service.description || "No description supplied in the catalogue."}</p><code>{service.operation_name}</code><div className="ai-service-status"><span>Governance: {service.status}</span><span>{draft.validation.contracts?.find((item) => item.node_id === node.id)?.resolution === "active" ? "Declared operation contract available" : "Operation contract unknown"}</span><span>Live availability unchecked</span></div></article>)}</>}
        <p className="ai-library-footnote">Runtime readiness is checked later in Build Solution. A catalogue record does not establish live availability.</p>
      </aside>

      <section className="ai-panel ai-workflow" aria-label="Workflow preview"><div className="ai-panel-title"><div><span className="ai-online-dot" />Workflow preview</div><span className="ai-tag">{draft ? `Revision ${draft.revision}` : "Start a design"}</span></div>
        {draft ? <><div className="ai-design-title"><h2>{preview?.name}</h2><span className={draft.dirty ? "ai-unsaved" : "ai-saved"}>{draft.dirty ? "Unsaved changes" : "Draft saved"}</span></div>
          {draft.pending && <div className="ai-proposal"><div><strong>Proposed changes</strong><span>Review before applying</span></div><ul>{draft.pending.turn.edits.map((edit, index) => <li key={index}>{edit.kind.replaceAll("_", " ")}: {edit.value}</li>)}</ul>
            <div className="ai-proposal-actions"><button onClick={() => setShowProposed((value) => !value)}>{showProposed ? "View current" : "Preview proposal"}</button><button className="ai-primary" disabled={!!busy || !draft.pending.validation.valid} onClick={() => action("Applying", async () => { const next = await api(`/drafts/${draft.id}/apply`, { revision: draft.revision, proposal_id: draft.pending!.id }); setDraft(next); setMessages((current) => [...current, { role: "assistant", content: "The validated changes are now applied to your draft. Select Save draft when you are ready." }]); })}>Apply changes</button></div>
            {!draft.pending.validation.valid && <p role="alert">{draft.pending.validation.errors.join(" ")}</p>}</div>}
          <div className="ai-canvas" data-preview={draft.pending && showProposed ? "proposed" : "current"}><ReactFlow key={`${draft.id}:${draft.revision}:${showProposed}:${draft.pending?.id || "current"}`} nodes={nodes} edges={preview?.edges || []} fitView fitViewOptions={{ padding: 0.18 }} nodesDraggable={false} nodesConnectable={false} elementsSelectable={false} deleteKeyCode={null} minZoom={0.25} maxZoom={1.4} aria-label="Saved service workflow"><Background gap={20} color="#ddd9ec" /><Controls showInteractive={false} /></ReactFlow><div className="ai-canvas-legend">{draft.pending && showProposed ? "PROPOSED · not yet applied" : "CURRENT DRAFT · not executed"}</div></div>
          <details className="ai-validation"><summary>{draft.validation.valid ? "Design checks complete" : "Input or catalogue review needed"}<span>Compatibility unverified</span></summary>{draft.validation.errors.map((message, index) => <p key={`e${index}`} className="ai-validation-error">{message}</p>)}{draft.validation.unknown.map((message, index) => <p key={index}>{message}</p>)}{draft.validation.required_inputs.map((input, index) => <p key={`r${index}`}>Required: {input.operation} / {input.name} — delivery {input.resolution}</p>)}<p>{draft.reference_note}</p><p>Reference revision: {draft.source.revision.slice(0, 12)}</p></details>
          {draft.design.input_policy && <details className="ai-validation"><summary>Supported run input</summary><pre>{JSON.stringify(draft.design.run_input, null, 2)}</pre><p>Wrapper schema evidence: {draft.design.input_policy.evidence_reference}</p><p>Input defaults will open in Build Solution for review.</p></details>}
          <div className="ai-draft-actions"><button disabled={!!busy || !draft.can_undo} onClick={() => action("Undoing", async () => setDraft(await api(`/drafts/${draft.id}/undo`, { revision: draft.revision })))}><Undo2 size={16} /> Undo</button><button className="ai-primary" disabled={!!busy || !draft.dirty || !draft.validation.valid} onClick={() => action("Saving", async () => { const value = await api(`/drafts/${draft.id}/save`, { revision: draft.revision }); setDraft(value.draft); setActivity((current) => [...current, ...value.activity].slice(-60)); })}><Save size={16} /> Save draft</button>{draft.saved_solution_id && !draft.dirty ? <Link href={`/builder?solutionId=${encodeURIComponent(draft.saved_solution_id)}`}>Open in Build Solution <ArrowRight size={15} /></Link> : <span className="ai-save-hint">Save to open in the builder</span>}</div>
        </> : <div className="ai-empty-workflow"><div className="ai-empty-icon"><Sparkles size={32} /></div><h2>A starting point for your next solution</h2><p>Describe your objective to find an existing workflow, or choose an available template to create your own editable copy.</p><div className="ai-empty-steps"><span>01 Describe</span><span>02 Adapt</span><span>03 Save & build</span></div></div>}
      </section>

      <section className="ai-panel ai-conversation" aria-label="Design conversation"><div className="ai-panel-title"><div><Sparkles size={17} /> Design assistant</div><span className="ai-tag">{config.provider_mode === "test" ? "Test provider" : config.provider_name || "AI"}</span></div>
        {config.provider_configured && <p className="ai-provider-label">Runtime model: {config.model || "Not configured"}</p>}
        <div className="ai-chat-history" role="log" aria-live="polite">{messages.length === 0 && <div className="ai-chat-welcome"><div className="ai-assistant-avatar"><Sparkles size={20} /></div><h2>What would you like to achieve?</h2><p>I can help you find an existing solution, explain how it works, and propose supported changes to your copy.</p><span>Every change stays yours to review.</span></div>}{messages.map((message, index) => <div key={index} className={`ai-message ${message.role}`}><small>{message.role === "user" ? "You" : "Studio assistant"}</small><p>{message.content}</p></div>)}
          {recommendation && <button className="ai-primary ai-create-recommendation" disabled={!!busy} onClick={() => start(recommendation)}>Create {templates.find((item) => item.key === recommendation)?.label} draft <ArrowRight size={15} /></button>}
          {busy && <div className="ai-thinking" role="status"><LoaderCircle size={16} className="ai-spin" />{busy}…</div>}<div ref={chatEnd} /></div>
        <div className="ai-examples">{(draft ? ["Explain the services and their connections", "Rename my draft to Energy design study", "Which inputs can I safely change?"] : startingPrompts(templates)).map((example) => <button key={example} disabled={!!busy || !chatEnabled} onClick={() => setPrompt(example)}>{example}<ArrowRight size={13} /></button>)}</div>
        <form className="ai-composer" onSubmit={(event) => { event.preventDefault(); void send(); }}><label htmlFor="design-prompt" className="ai-sr-only">Describe your objective or request a change</label><textarea id="design-prompt" value={prompt} maxLength={4000} rows={3} disabled={!chatEnabled || !!busy} onChange={(event) => setPrompt(event.target.value)} placeholder={allowancePaused ? "AI testing is paused by the local test allowance" : config.provider_configured ? "Describe your objective or request a change…" : "AI provider not configured"} /><div><small>Review proposals before applying.</small>{busy === "Thinking" ? <button type="button" onClick={() => controller.current?.abort()}><X size={15} /> Cancel</button> : <button className="ai-primary" aria-label="Send request" disabled={!!busy || !prompt.trim() || !chatEnabled}><Send size={16} /></button>}</div></form>
        <details className="ai-activity"><summary><MessageSquare size={14} /> Activity <span>{activity.length} events</span><ChevronDown size={14} /></summary>{activity.length ? <ol>{activity.map((event, index) => <li key={index}><code>{event.tool}</code><span>{event.status} · {event.summary}</span></li>)}</ol> : <p>Actual tool calls will appear here when a request runs.</p>}</details>
      </section>
    </div>
  </div>;
}
