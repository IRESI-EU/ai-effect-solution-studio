"use client";

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Background, Controls, ReactFlow, type Edge, type Node, Position } from "@xyflow/react";
import { ArrowRight, Check, ChevronDown, LoaderCircle, MessageSquare, Save, Send, Sparkles, Undo2, X } from "lucide-react";
import "@xyflow/react/dist/style.css";
import { useAuth } from "../../components/auth-context";
import { apiErrorMessage } from "../../lib/solution-design";
import { allowanceFromError, startingPrompts, type TestAllowance } from "./allowance";
import { activeDraftId, conversationKey, conversationForCopy, draftUrl, readConversation, readRecommendation, type Message, type Activity, type Recommendation } from "./session";
import "./workspace.css";
import StructuralReview, { type StructuralReviewData } from "../../components/structural-review";
import InstanceSettingReview, { type ParameterReview } from "../../components/instance-setting-review";

type Validation = { valid: boolean; errors: string[]; unknown: string[]; contracts?: {node_id: string; resolution: string; version: string | null}[]; required_inputs: { operation: string; name: string; resolution: string }[] };
type Design = { name: string; description: string; nodes: Node[]; edges: Edge[]; editing_scope?: string; run_input: Record<string, unknown> | null; input_policy: { evidence_reference: string; json_schema: Record<string, unknown> } | null };
type InstanceSettings = { node_id: string; label: string; resolution: string; limitation?: string; effective_parameters?: Record<string, unknown>; definition?: { properties: Record<string, { title: string }> } };
type Draft = { id: string; revision: number; template_key: string; design: Design; instance_settings?: InstanceSettings[]; validation: Validation; dirty: boolean; saved_solution_id: string | null; can_undo: boolean; reference_note: string; source: { revision: string }; pending: { id: string; design: Design; turn: { edits: { kind: string; value: string; node_id: string | null }[] }; parameter_review?: ParameterReview; structural_review?: StructuralReviewData; validation: Validation } | null };
type Template = { key: string; label: string; description?: string; available: boolean; guided_available?: boolean; editing_scope?: string; reason?: string; operations?: string[] };
type ResumeDraft = { id: string; name: string; updated_at: string; dirty: boolean; saved_solution_id: string | null; pending_changes: boolean; seed: number | null };
type SwitchTarget = { kind: "start"; key: string; carryDiscovery?: boolean } | { kind: "resume"; id: string } | { kind: "home" };
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
    return { ...node, width: 245, height: 64, measured: { width: 245, height: 64 }, position: { x: 0, y: Math.max(ordered.indexOf(node.id), 0) * 125 }, sourcePosition: Position.Bottom, targetPosition: Position.Top,
      data: { ...node.data, label: <div className="ai-graph-label"><span>{String(node.data?.label || service?.name || node.id)}</span></div> },
      style: { width: 245, height: 64, boxSizing: "border-box", borderRadius: 12, border: `1px solid ${service ? "#c9bbfb" : "#dedde9"}`, background: service ? "#f6f3ff" : "white", color: "#24204c", padding: 13 } };
  });
}

export default function DesignAIPage() {
  return <Suspense fallback={<div className="ai-page">Loading design workspace…</div>}><DesignAIRoute /></Suspense>;
}

function DesignAIRoute() {
  const params = useSearchParams();
  const { user } = useAuth();
  const draftId = activeDraftId(params);
  // Remount all draft/conversation state together, including on same-page navigation.
  return <DesignWorkspace key={`${user?.id || "signed-out"}:${draftId || "start"}`} draftId={draftId} />;
}

function DesignWorkspace({ draftId }: { draftId: string | null }) {
  const { user } = useAuth();
  const router = useRouter();
  const [config, setConfig] = useState<{ enabled: boolean; provider_configured: boolean; provider_name?: string; provider_mode?: string; model?: string | null; test_allowance?: TestAllowance } | null>(null);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [resumeDrafts, setResumeDrafts] = useState<ResumeDraft[]>([]);
  const [loadingDraft, setLoadingDraft] = useState(!!draftId);
  const [conversationReady, setConversationReady] = useState(false);
  const [historyUnavailable, setHistoryUnavailable] = useState(false);
  const [conversationWarning, setConversationWarning] = useState("");
  const [switchTarget, setSwitchTarget] = useState<SwitchTarget | null>(null);
  const lastRevision = useRef<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [activity, setActivity] = useState<Activity[]>([]);
  const [prompt, setPrompt] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [retryPrompt, setRetryPrompt] = useState("");
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null);
  const [showProposed, setShowProposed] = useState(true);
  const [seed, setSeed] = useState("42");
  const controller = useRef<AbortController | null>(null);
  const inFlight = useRef(false);
  const chatEnd = useRef<HTMLDivElement | null>(null);
  const sessionKey = user ? conversationKey(user.id, draftId) : null;
  const allowance = config?.test_allowance;
  const allowancePaused = !!allowance && !allowance.can_request;
  const chatEnabled = !!config?.provider_configured && !allowancePaused;

  async function refreshAllowance() {
    try { setConfig(await api("/config")); }
    catch { /* Keep the last known allowance state; the server still enforces it. */ }
  }

  async function initialize(signal?: AbortSignal) {
    setError("");
    try {
      const value = await api("/config", undefined, signal); setConfig(value);
      if (value.enabled) {
        const [choices, previous] = await Promise.all([api("/templates", undefined, signal), api("/drafts", undefined, signal)]);
        if (signal?.aborted) return;
        setTemplates(choices); setResumeDrafts(previous);
        const selected: Draft | null = draftId ? await api(`/drafts/${encodeURIComponent(draftId)}`, undefined, signal) : null;
        if (signal?.aborted) return;
        let retained = null;
        try { retained = readConversation(sessionKey ? localStorage.getItem(sessionKey) : null, user!.id, draftId); }
        catch { setConversationWarning("This browser cannot retain conversation history. Your draft is stored separately."); }
        setDraft(selected); setMessages(retained?.messages || []); setActivity(retained?.activity || []);
        setPrompt(retained?.prompt || ""); setSeed(retained?.seedInput ?? String(selected?.design.run_input?.seed ?? 42));
        setRecommendation(retained?.recommendation || null);
        setHistoryUnavailable(retained?.historyUnavailable ?? !!draftId); setConversationReady(true);
      }
    } catch (failure) {
      if (!signal?.aborted) setError(failure instanceof Error ? failure.message : "The workspace could not be loaded.");
    } finally { if (!signal?.aborted) setLoadingDraft(false); }
  }
  useEffect(() => {
    const abort = new AbortController();
    if (user) void initialize(abort.signal);
    return () => { abort.abort(); controller.current?.abort(); };
  }, [user?.id, draftId]);
  useEffect(() => {
    if (!sessionKey || !conversationReady || !user) return;
    try { localStorage.setItem(sessionKey, JSON.stringify({ ownerId: user.id, draftId: draft?.id ?? null, messages, activity, prompt, seedInput: seed, historyUnavailable, recommendation })); }
    catch { setConversationWarning("This browser cannot retain conversation history. Your draft is stored separately."); }
  }, [sessionKey, draft?.id, conversationReady, messages, activity, prompt, seed, historyUnavailable, recommendation]);
  useEffect(() => {
    if (!draft) return;
    if (lastRevision.current !== null && lastRevision.current !== draft.revision) setSeed(String(draft.design.run_input?.seed ?? 42));
    lastRevision.current = draft.revision;
  }, [draft?.revision]);
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

  async function navigate(target: SwitchTarget) {
    setSwitchTarget(null);
    if (target.kind === "start") {
      await action("Creating copy", async () => {
        const value: Draft = await api("/drafts", { template_key: target.key, guided: target.key === "dutch" && templates.find(item => item.key === target.key)?.editing_scope !== "append_bound_operation" });
        try { localStorage.setItem(conversationKey(user!.id, value.id), JSON.stringify(conversationForCopy(user!.id, value.id, { ownerId: user!.id, draftId, messages, activity, prompt, seedInput: seed, historyUnavailable, recommendation }, !!target.carryDiscovery))); }
        catch { /* Draft creation remains usable when browser storage is unavailable. */ }
        router.push(draftUrl(value.id));
      });
    } else router.push(target.kind === "home" ? "/design-ai" : draftUrl(target.id));
  }

  function requestSwitch(target: SwitchTarget) {
    if (inFlight.current) return;
    if (draft && (draft.dirty || draft.pending || prompt.trim() || seed !== String(draft.design.run_input?.seed ?? 42))) setSwitchTarget(target);
    else void navigate(target);
  }

  function start(key: string) { requestSwitch({ kind: "start", key }); }

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
        setRecommendation(readRecommendation(value.recommendation));
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
  const dutch = templates.find(item => item.key === "dutch");
  const structuralTemplates = templates.filter(item => item.editing_scope === "append_bound_operation");
  const settingsTemplates = templates.filter(item => item.editing_scope === "instance_settings");
  const guided = draft?.template_key === "dutch" && !!draft.design.input_policy;
  const seedSchema = draft?.design.input_policy?.json_schema.properties as Record<string, { enum?: number[] }> | undefined;
  const seedChoices = seedSchema?.seed?.enum;

  if (!config || loadingDraft) return <div className="ai-page"><h1>Design with AI</h1>{error ? <div role="alert">{error} <button onClick={() => void initialize()}>Retry</button></div> : <p>Loading design workspace…</p>}</div>;
  if (!config.enabled) return <div className="ai-page"><h1>Design with AI</h1><div className="card ai-disabled"><Sparkles /><h2>The AI design pilot is not enabled</h2><p>Your administrator can enable it in a private development or staging environment.</p><Link href="/builder">Open Build Solution <ArrowRight size={15} /></Link></div></div>;

  return <div className="ai-page">
    <div className="ai-heading"><div><div className="ai-eyebrow"><Sparkles size={15} /> SOLUTION STUDIO <span>PILOT</span></div><h1>Design with AI</h1><p>{draft ? "Review your experiment. Save when you are ready." : "Describe your objective. Review a recommendation before creating an experiment."}</p></div><Link href="/builder">Build Solution <ArrowRight size={16} /></Link></div>
    {config.provider_mode === "test" && <div className="ai-config-notice" role="status"><strong>OFFLINE TEST FIXTURE</strong><span>Responses are provider-boundary test data. No AI provider call or experiment execution occurs.</span></div>}
    {draft && <div className="ai-session-heading"><span>Active experiment · {draft.id.slice(0, 8)}</span><button disabled={!!busy} onClick={() => requestSwitch({ kind: "home" })}>Choose another experiment</button></div>}
    {switchTarget && <div className="ai-alert" role="alert"><span>Your current work has unsaved changes or a pending review. It will remain available to resume; no draft will be deleted.</span><button onClick={() => setSwitchTarget(null)}>Stay with this experiment</button><button onClick={() => void navigate(switchTarget)}>Continue to {switchTarget.kind === "start" ? "new experiment" : switchTarget.kind === "home" ? "experiment choices" : "selected experiment"}</button></div>}
    {error && <div className="ai-alert" role="alert">{error} <button onClick={() => draft ? action("Refreshing", async () => setDraft(await api(`/drafts/${draft.id}`))) : initialize()}>Refresh</button>{retryPrompt && <button disabled={!!busy || !chatEnabled} onClick={() => send(retryPrompt, true)}>Retry request</button>}</div>}
    {!config.provider_configured && <div className="ai-config-notice" role="status"><Sparkles size={17} /><div><strong>AI provider not configured</strong><span>You can explore configured templates, create a copy and save it. Conversation needs a server-side provider connection.</span></div></div>}
    {allowance && <div className="ai-config-notice" role="status" data-testid="test-allowance"><Sparkles size={17} /><div><strong>{allowancePaused ? "Send paused" : "Manual AI messages available"}</strong><span>{allowance.message}</span>{allowancePaused && <span>Guided controls remain available: start or resume an experiment, review its settings and save.</span>}{allowance.remaining_calls !== undefined && <span>{Math.min(allowance.remaining_calls, allowance.task_allowance?.remaining_calls ?? allowance.remaining_calls)} manual messages available under the active checkpoint · shared allowance US${allowance.remaining_usd?.toFixed(5)} · maximum reservation US${allowance.next_reservation_usd?.toFixed(3)} per message.{allowance.task_allowance && ` Task reservation limit US$${allowance.task_allowance.limit_usd.toFixed(3)}; already reserved US$${allowance.task_allowance.reserved_usd.toFixed(3)}.`}</span>}</div><button disabled={!!busy} onClick={() => void refreshAllowance()}>Check allowance</button></div>}
    <div className={`ai-workspace ${!draftId ? `ai-discovery ${messages.length === 0 ? "ai-discovery-empty" : ""}` : ""}`}>
      <aside className="ai-panel ai-library"><div className="ai-panel-title"><span>Design library</span><span className="ai-count">{(dutch?.guided_available ? 1 : 0) + settingsTemplates.filter(item => item.available).length + structuralTemplates.filter(item => item.available).length}</span></div>
        <p className="ai-panel-intro">Choose an experiment</p>
        {!structuralTemplates.length && <div className="ai-templates"><button className="ai-template" disabled={!dutch?.guided_available || !!busy} onClick={() => start("dutch")}>
          <span className="ai-template-name">Generate and benchmark a sample electricity grid.</span><small>{draft ? "Start a separate experiment" : "Start experiment"} <ArrowRight size={13} /></small>
        </button></div>}
        {structuralTemplates.map(item => <div key={item.key} className="ai-templates"><button className="ai-template" disabled={!item.available || !!busy} onClick={() => start(item.key)}><span className="ai-template-name">Compose a connected analyzer · {item.label}</span><small>Create a separate structural copy <ArrowRight size={13} /></small></button><p className="ai-panel-intro">Add one compatible analyzer and its named connection. Existing settings stay unchanged. Design preparation only.</p>{!item.available && <p role="status">{item.reason}</p>}</div>)}
        {settingsTemplates.map(item => <div key={item.key} className="ai-templates"><button className="ai-template" disabled={!item.available || !!busy} onClick={() => start(item.key)}><span className="ai-template-name">Edit instance settings · {item.label}</span><small>Create a separate settings copy <ArrowRight size={13} /></small></button><p className="ai-panel-intro">Existing steps and connections stay fixed. Review, Apply and Save setting changes only.</p>{!item.available && <p className="ai-panel-intro" role="status">Settings unavailable: {item.reason}</p>}</div>)}
        {!structuralTemplates.length && <p className="ai-panel-intro">Generate a sample grid with the approved local Dutch template, then benchmark that grid. You will receive a grid summary, recorded benchmark values and optional downloads.</p>}
        {!structuralTemplates.length && !dutch?.guided_available && <p className="ai-panel-intro" role="status">This experiment is unavailable. {dutch?.reason || "The approved seed settings could not be verified."}</p>}
        <details className="ai-resume"><summary>Resume existing experiment ({resumeDrafts.length})</summary>{resumeDrafts.length ? <div className="ai-resume-list">{resumeDrafts.map(item => <article key={item.id}><strong>{item.name}</strong><span>{item.saved_solution_id ? item.dirty ? "Saved copy with unsaved changes" : "Saved copy" : "Unsaved draft"}{item.pending_changes ? " · proposal awaiting review" : ""}</span><span>{item.seed !== null ? `Seed ${item.seed} · ` : ""}{new Date(item.updated_at.endsWith("Z") ? item.updated_at : `${item.updated_at}Z`).toLocaleString()} · {item.id.slice(0, 8)}</span><button disabled={!!busy || item.id === draft?.id} aria-label={`Resume ${item.name} ${item.id.slice(0, 8)}`} onClick={() => requestSwitch({ kind: "resume", id: item.id })}>{item.id === draft?.id ? "Currently open" : "Resume"}</button></article>)}</div> : <p>No earlier experiments yet. Start one above.</p>}</details>
        {draft && <><div className="ai-panel-title ai-service-heading">Services in this design <span className="ai-count">{services.length}</span></div>{services.map(({ node, service }, index) => <article className="ai-service" key={node.id}><div className="ai-service-top"><span>{String(index + 1).padStart(2, "0")}</span><strong>{guided ? service.operation_name === "ConfigureAndSynthesize" ? "Generate sample grid." : "Benchmark grid." : service.name}</strong></div><details><summary>Service details</summary><p>{service.description || "No description supplied in the catalogue."}</p><code>{service.id}</code><br /><code>{service.operation_name}</code><div className="ai-service-status"><span>Governance: {service.status}</span><span>{draft.validation.contracts?.find((item) => item.node_id === node.id)?.resolution === "active" ? "Declared operation contract available" : "Operation contract unknown"}</span><span>Live availability unchecked</span></div></details></article>)}</>}
        <p className="ai-library-footnote">Runtime readiness is checked later in Build Solution. A catalogue record does not establish live availability.</p>
      </aside>

      <section className="ai-panel ai-workflow" aria-label="Workflow preview"><div className="ai-panel-title"><div><span className="ai-online-dot" />Workflow preview</div><span className="ai-tag">{draft ? `Revision ${draft.revision}` : draftId ? "Unavailable" : "No experiment created"}</span></div>
        {draft ? <><div className="ai-design-title"><h2>{preview?.name}</h2><span className={draft.dirty ? "ai-unsaved" : "ai-saved"}>{draft.dirty ? "Unsaved changes" : draft.saved_solution_id ? "Draft saved" : "Draft retained"}</span></div>
          {draft.instance_settings && <div className="ai-instance-settings" aria-label="Current instance settings"><p>Current applied settings · draft revision {draft.revision}. Use the instance label when requesting a change.</p>{draft.instance_settings.map(instance => <div key={instance.node_id}><strong>{instance.label}</strong>{instance.resolution === "active" ? <p>{Object.entries(instance.effective_parameters || {}).map(([key, value]) => `${instance.definition?.properties[key]?.title || key}: ${String(value)}`).join(" · ")}</p> : <p role="status">Settings unavailable: {instance.limitation}</p>}<details><summary>Instance identifier</summary><code>{instance.node_id}</code></details></div>)}</div>}
          {draft.pending && <div className="ai-proposal"><div><strong>Proposed changes</strong><span>Review before applying</span></div>{draft.pending.structural_review ? <StructuralReview review={draft.pending.structural_review} /> : draft.pending.parameter_review?.changes.length ? <InstanceSettingReview review={draft.pending.parameter_review} /> : <ul>{draft.pending.turn.edits.map((edit, index) => <li key={index}>{guided && edit.kind === "set_run_input" ? `Grid seed: ${String(draft.pending?.design.run_input?.seed ?? "not set")}` : `${edit.kind.replaceAll("_", " ")}${edit.node_id ? ` (${edit.node_id})` : ""}: ${edit.value}`}</li>)}</ul>}
            <div className="ai-proposal-actions"><button onClick={() => setShowProposed((value) => !value)}>{showProposed ? "View current" : "Preview proposal"}</button><button className="ai-primary" disabled={!!busy || !draft.pending.validation.valid} onClick={() => action("Applying", async () => { const next = await api(`/drafts/${draft.id}/apply`, { revision: draft.revision, proposal_id: draft.pending!.id }); setDraft(next); setMessages((current) => [...current, { role: "assistant", content: "The validated changes are now applied to your draft. Select Save draft when you are ready." }]); })}>Apply changes</button></div>
            {!draft.pending.validation.valid && <p role="alert">{draft.pending.validation.errors.join(" ")}</p>}</div>}
          {guided && <p className="ai-panel-intro">Generate sample grid → Benchmark grid. The generated grid is passed directly to the benchmark; no dataset upload is needed.</p>}
          <div className="ai-canvas" data-preview={draft.pending && showProposed ? "proposed" : "current"}><ReactFlow key={`${draft.id}:${draft.revision}:${showProposed}:${draft.pending?.id || "current"}`} nodes={nodes} edges={preview?.edges || []} fitView fitViewOptions={{ padding: 0.08, minZoom: 0.85, maxZoom: 1 }} nodesDraggable={false} nodesConnectable={false} elementsSelectable={false} deleteKeyCode={null} minZoom={0.25} maxZoom={1.4} aria-label="Active experiment workflow"><Background gap={20} color="#ddd9ec" /><Controls showInteractive={false} /></ReactFlow><div className="ai-canvas-legend">{draft.pending && showProposed ? "PROPOSED · not yet applied" : "CURRENT DRAFT · design view"}</div></div>
          <details className="ai-validation"><summary>{draft.validation.valid ? "Design checks complete" : "Input or catalogue review needed"}<span>{draft.design.editing_scope === "append_bound_operation" ? "Design bindings checked · runtime unchecked" : "Compatibility unverified"}</span></summary>{draft.validation.errors.map((message, index) => <p key={`e${index}`} className="ai-validation-error">{message}</p>)}{draft.validation.unknown.map((message, index) => <p key={index}>{message}</p>)}{draft.validation.required_inputs.map((input, index) => <p key={`r${index}`}>Required: {input.operation} / {input.name} — delivery {input.resolution}</p>)}<p>{draft.reference_note}</p><p>Reference revision: {draft.source.revision.slice(0, 12)}</p></details>
          {guided ? <div className="ai-guided-settings"><strong>Settings: seed {String(draft.design.run_input?.seed ?? "not set")}</strong><p>{draft.dirty ? "Save your draft, then review and check readiness in Build Solution." : "Your saved settings are ready to review in Build Solution."}</p><details><summary>Advanced settings (optional)</summary><label htmlFor="grid-seed">Grid seed</label>{seedChoices ? <select id="grid-seed" value={seed} onChange={event => setSeed(event.target.value)}>{seedChoices.map(value => <option key={value} value={value}>{value}</option>)}</select> : <input id="grid-seed" type="number" step="1" value={seed} onChange={event => setSeed(event.target.value)} />}<p>The seed controls the generator's random choices. Only settings accepted by the approved wrapper are supported.</p><button disabled={!!busy || !seed.trim() || !Number.isSafeInteger(Number(seed)) || Number(seed) === draft.design.run_input?.seed} onClick={() => action("Reviewing settings", async () => { setDraft(await api(`/drafts/${draft.id}/guided-settings`, { revision: draft.revision, seed: Number(seed) })); setShowProposed(true); })}>Review seed change</button><p>Review the proposal above, select Apply changes, then Save draft. Undo restores the previous applied settings.</p></details></div> : draft.design.input_policy && <details className="ai-validation"><summary>Supported run input</summary><pre>{JSON.stringify(draft.design.run_input, null, 2)}</pre><p>Wrapper schema evidence: {draft.design.input_policy.evidence_reference}</p></details>}
          <div className="ai-draft-actions"><button disabled={!!busy || !draft.can_undo} onClick={() => action("Undoing", async () => setDraft(await api(`/drafts/${draft.id}/undo`, { revision: draft.revision })))}><Undo2 size={16} /> Undo</button><button className="ai-primary" disabled={!!busy || !draft.dirty || !draft.validation.valid} onClick={() => action("Saving", async () => { const value = await api(`/drafts/${draft.id}/save`, { revision: draft.revision }); setDraft(value.draft); setActivity((current) => [...current, ...value.activity].slice(-60)); })}><Save size={16} /> Save draft</button>{draft.saved_solution_id && !draft.dirty ? <Link href={`/builder?solutionId=${encodeURIComponent(draft.saved_solution_id)}`}>Open in Build Solution <ArrowRight size={15} /></Link> : <span className="ai-save-hint">Save to open in the builder</span>}</div>
        </> : draftId ? <div className="ai-empty-workflow"><h2>Experiment could not be opened</h2><p>Your other work is unchanged. Choose an experiment or resume another draft.</p><Link href="/design-ai">Back to experiment choices</Link></div> : <div className="ai-empty-workflow"><div className="ai-empty-icon"><Sparkles size={32} /></div><h2>Your workflow will appear here</h2><p>No experiment has been created. Describe your objective to explore supported capabilities, then review a recommendation and choose Create this experiment. You can also use the library or Resume.</p><div className="ai-empty-steps"><span>01 Choose</span><span>02 Review</span><span>03 Save & build</span></div></div>}
      </section>

      <section className="ai-panel ai-conversation" aria-label="Design conversation"><div className="ai-panel-title"><div><Sparkles size={17} /> Design assistant</div><span className="ai-tag">{config.provider_mode === "test" ? "Test provider" : config.provider_name || "AI"}</span></div>
        {config.provider_configured && config.provider_mode !== "test" && <p className="ai-provider-label">Runtime model: {config.model || "Not configured"}</p>}
        {draft && <p className="ai-conversation-context">Conversation for <strong>{draft.design.name}</strong> · {draft.id.slice(0, 8)}{historyUnavailable ? ". Earlier conversation was not retained in this browser; it has not been recreated." : ". Messages shown here belong to this experiment."}</p>}
        {conversationWarning && <p className="ai-conversation-context" role="status">{conversationWarning}</p>}
        <div className="ai-chat-history" role="log" aria-live="polite">{draft && messages.length === 0 && <p className="ai-panel-intro">No retained messages for this experiment. {allowancePaused ? "Chat is paused; use the guided controls to continue." : "Ask about this experiment when you are ready."}</p>}{!draft && !draftId && messages.length === 0 && <div className="ai-chat-welcome"><div className="ai-assistant-avatar"><Sparkles size={20} /></div><h2>What would you like to explore?</h2><p>Describe your objective below. I can look up the enabled approved capabilities and recommend a supported experiment before you create a copy.</p><span>{allowancePaused ? "You can type your objective now. Send is paused by the allowance shown above." : "Sending a message uses the manual AI allowance. Nothing is created or executed by discovery."}</span></div>}{messages.map((message, index) => <div key={index} className={`ai-message ${message.role}`}><small>{message.role === "user" ? "You" : "Studio assistant"}</small><p>{message.content}</p></div>)}
          {!draft && recommendation && <div className="ai-discovery-card"><strong>Suggested experiment</strong><h3>{recommendation.label}</h3><p>Verified local capabilities:</p><ol>{recommendation.steps.map(step => <li key={step.operation}>{step.title}</li>)}</ol><p>{recommendation.connection}.</p><p>Expected after successful execution and capture: {recommendation.expected_result_view.join(", ")}.</p><p>Optional downloads: {recommendation.optional_downloads.join(", ")}.</p><p>{recommendation.availability}. No experiment has been created or run by this conversation.</p><details><summary>Limitations</summary><ul>{recommendation.limitations.map(item => <li key={item}>{item}</li>)}</ul></details><button className="ai-primary ai-create-recommendation" disabled={!!busy || recommendation.key !== "dutch" || !dutch?.guided_available} onClick={() => requestSwitch({kind:"start",key:recommendation.key,carryDiscovery:true})}>Create this experiment <ArrowRight size={15} /></button>{!dutch?.guided_available && <p>This earlier recommendation is no longer available. Your conversation is retained.</p>}</div>}
          {busy && <div className="ai-thinking" role="status"><LoaderCircle size={16} className="ai-spin" />{busy}…</div>}<div ref={chatEnd} /></div>
        <div className="ai-examples">{(draft?.design.editing_scope === "append_bound_operation" ? ["Add a benchmark step after the grid generator and use the grid it produces. Keep the generator settings unchanged.", "Explain the supported connection and its limitations"] : draft?.design.editing_scope === "instance_settings" ? ["Which instance settings are available?", "Explain the current instance settings"] : draft ? ["Explain the services and their connections", "Rename my draft to Energy design study", "Which inputs can I safely change?"] : startingPrompts(templates.filter(item => item.key === "dutch" && item.guided_available))).map((example) => <button key={example} disabled={!!busy} onClick={() => setPrompt(example)}>{example}<ArrowRight size={13} /></button>)}</div>
        <form className="ai-composer" onSubmit={(event) => { event.preventDefault(); void send(); }}><label htmlFor="design-prompt" className="ai-sr-only">Describe your objective or request a change</label><textarea id="design-prompt" value={prompt} maxLength={4000} rows={3} disabled={!!busy} onChange={(event) => setPrompt(event.target.value)} placeholder={draft ? "Ask about this experiment or request a supported change…" : "Describe what you want to explore…"} /><div><small>{!chatEnabled ? "You can type; Send is unavailable. See the allowance or provider notice above." : draft ? "Review proposals before applying." : "Send only when you want to use one manual AI message."}</small>{busy === "Thinking" ? <button type="button" onClick={() => controller.current?.abort()}><X size={15} /> Cancel</button> : <button className="ai-primary" aria-label="Send request" disabled={!!busy || !prompt.trim() || !chatEnabled}><Send size={16} /></button>}</div></form>
        <details className="ai-activity"><summary><MessageSquare size={14} /> Activity <span>{activity.length} events</span><ChevronDown size={14} /></summary>{activity.length ? <ol>{activity.map((event, index) => <li key={index}><code>{event.tool}</code><span>{event.status} · {event.summary}</span></li>)}</ol> : <p>Actual tool calls will appear here when a request runs.</p>}</details>
      </section>
    </div>
  </div>;
}
