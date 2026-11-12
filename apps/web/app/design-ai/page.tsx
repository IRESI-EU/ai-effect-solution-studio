"use client";

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Background, Controls, ReactFlow, type Edge, type Node, Position } from "@xyflow/react";
import { ArrowRight, LoaderCircle, Save, Send, Sparkles, Undo2, X } from "lucide-react";
import "@xyflow/react/dist/style.css";
import { useAuth } from "../../components/auth-context";
import { apiErrorMessage } from "../../lib/solution-design";
import { allowanceFromError, type TestAllowance } from "./allowance";
import { activeDraftId, activeConversationId, conversationUrl, conversationKey, conversationForCopy, draftUrl, readConversation, readRecommendation, recommendationCreation, boundedHistory, readClarification, type Clarification, type Message, type Activity, type Recommendation } from "./session";
import "./workspace.css";
import WorkspaceViewport from "./workspace-viewport";
import ReviewDialog from "../../components/review-dialog";
import {designStage,nodeReview,supportedExamples,nextWorkspaceArea,promptPlaceholder,type WorkspaceArea} from "./workspace-view";
import DiscoveryRecommendation from "../../components/discovery-recommendation";
import ConversationMessage from "../../components/conversation-message";
import ExperimentExecution from "../../components/experiment-execution";
import CompositionReview, { type CompositionReviewData } from "../../components/composition-review";
import StructuralReview, { type StructuralReviewData } from "../../components/structural-review";
import InstanceSettingReview, { type ParameterReview } from "../../components/instance-setting-review";

type Validation = { valid: boolean; errors: string[]; unknown: string[]; contracts?: {node_id: string; resolution: string; version: string | null}[]; required_inputs: { operation: string; name: string; resolution: string }[] };
type Design = { name: string; description: string; nodes: Node[]; edges: Edge[]; editing_scope?: string; run_input: Record<string, unknown> | null; input_policy: { evidence_reference: string; json_schema: Record<string, unknown> } | null };
type InstanceSettings = { node_id: string; label: string; resolution: string; limitation?: string; effective_parameters?: Record<string, unknown>; definition?: { properties: Record<string, { title: string }> } };
type Draft = { id: string; guided_experiment?: string; revision: number; template_key?: string; design: Design; instance_settings?: InstanceSettings[]; validation: Validation; dirty: boolean; saved_solution_id: string | null; can_undo: boolean; reference_note: string; source: { revision: string; kind?: string }; pending: { id: string; design: Design; turn: { edits: { kind: string; value: string; node_id: string | null }[] }; composition_review?: CompositionReviewData; parameter_review?: ParameterReview; structural_review?: StructuralReviewData; validation: Validation } | null };
type Template = { key: string; label: string; description?: string; available: boolean; guided_available?: boolean; qualified_experiment?: boolean; editing_scope?: string; reason?: string; operations?: string[] };
type ResumeDraft = { id: string; name: string; updated_at: string; dirty: boolean; saved_solution_id: string | null; pending_changes: boolean; seed: number | null };
type SwitchTarget = { kind: "start"; key: string; carryDiscovery?: boolean } | { kind: "resume" | "conversation"; id: string } | { kind: "home" };
type CatalogueService = { id: string; name: string; description: string; operation_name: string; status: string; version: string };

function appliedSeed(draft: Draft | null) {
  return draft?.guided_experiment === "qualified_dutch_grid"
    ? draft.instance_settings?.find(instance => instance.effective_parameters?.seed !== undefined)?.effective_parameters?.seed
    : draft?.design.run_input?.seed;
}

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
  const conversationId = draftId ? null : activeConversationId(params);
  // Remount all draft/conversation state together, including on same-page navigation.
  return <DesignWorkspace key={`${user?.id || "signed-out"}:${draftId || conversationId || "start"}`} draftId={draftId} conversationId={conversationId} />;
}

function DesignWorkspace({ draftId, conversationId }: { draftId: string | null; conversationId: string | null }) {
  const { user } = useAuth();
  const router = useRouter();
  const [config, setConfig] = useState<{ enabled: boolean; provider_configured: boolean; provider_name?: string; provider_mode?: string; model?: string | null; pilot_notice?: string; test_allowance?: TestAllowance } | null>(null);
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
  const [area,setArea] = useState<WorkspaceArea>("canvas");
  const [selectedId,setSelectedId] = useState<string|null>(null);
  const [technical,setTechnical] = useState(false);
  const selectionOrigin = useRef<HTMLElement|null>(null);
  const inspectorHeading = useRef<HTMLHeadingElement>(null);
  function chooseArea(value:WorkspaceArea) { setArea(value); try {sessionStorage.setItem(`design-ai-area:${user?.id}`,value);} catch {} }
  useEffect(()=>{try {const value=sessionStorage.getItem(`design-ai-area:${user?.id}`);if(value==="library"||value==="canvas"||value==="assistant")setArea(value);} catch {}},[user?.id]);
  useEffect(()=>{inspectorHeading.current?.focus();},[selectedId]);
  const [seed, setSeed] = useState("42");
  const [clarification,setClarification] = useState<Clarification|null>(null);
  const controller = useRef<AbortController | null>(null);
  const inFlight = useRef(false);
  const chatEnd = useRef<HTMLDivElement | null>(null);
  const sessionKey = user ? conversationKey(user.id, draftId, conversationId) : null;
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
        setPrompt(retained?.prompt || ""); setSeed(retained?.seedInput ?? String(appliedSeed(selected) ?? 42));
        setRecommendation(retained?.recommendation || null);
        setClarification(retained?.clarification || null);
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
    try { localStorage.setItem(sessionKey, JSON.stringify({ ownerId: user.id, draftId: draft?.id ?? null, messages, activity, prompt, seedInput: seed, historyUnavailable, recommendation, clarification })); }
    catch { setConversationWarning("This browser cannot retain conversation history. Your draft is stored separately."); }
  }, [sessionKey, draft?.id, conversationReady, messages, activity, prompt, seed, historyUnavailable, recommendation, clarification]);
  useEffect(() => {
    if (!draft) return;
    if (lastRevision.current !== null && lastRevision.current !== draft.revision) setSeed(String(appliedSeed(draft) ?? 42));
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
        const creation = target.carryDiscovery ? recommendationCreation(recommendation) : { template_key: target.key,
          guided: target.key === "dutch" && templates.find(item => item.key === target.key)?.editing_scope !== "append_bound_operation" };
        if (!creation) throw new Error("This capability has no supported creation path. Request a current registered workflow or catalogue-pair recommendation.");
        const value: Draft = await api("/drafts", creation);
        try { localStorage.setItem(conversationKey(user!.id, value.id), JSON.stringify(conversationForCopy(user!.id, value.id, { ownerId: user!.id, draftId, messages, activity, prompt, seedInput: seed, historyUnavailable, recommendation }, !!target.carryDiscovery))); }
        catch { /* Draft creation remains usable when browser storage is unavailable. */ }
        router.push(draftUrl(value.id));
      });
    } else router.push(target.kind === "home" ? "/design-ai" : target.kind === "conversation" ? conversationUrl(target.id) : draftUrl(target.id));
  }

  function requestSwitch(target: SwitchTarget) {
    if (inFlight.current) return;
    if (draft && (draft.dirty || draft.pending || prompt.trim() || seed !== String(appliedSeed(draft) ?? 42))) setSwitchTarget(target);
    else void navigate(target);
  }

  function start(key: string) { requestSwitch({ kind: "start", key }); }

  async function send(text = prompt, retry = false) {
    if (!text.trim() || inFlight.current || !chatEnabled) return;
    const before = messages;
    let history:Message[];
    try { history=boundedHistory(before); }
    catch(failure) {setError(failure instanceof Error?failure.message:"Conversation context unavailable; no request sent.");return;}
    if (!retry) setMessages((current) => [...current, { role: "user", content: text }]);
    setPrompt(""); setRetryPrompt("");
    if (!draft) setRecommendation(null);
    await action("Thinking", async () => {
      const abort = new AbortController(); controller.current = abort;
      try {
        const value = await api("/chat", { message: text, draft_id: draft?.id || null, revision: draft?.revision ?? null,
          history, clarification }, abort.signal);
        setMessages((current) => [...current, { role: "assistant", content: value.message }]);
        setActivity((current) => [...current, ...value.activity].slice(-60));
        if (value.draft) { setDraft(value.draft); setShowProposed(true); }
        setRecommendation(readRecommendation(value.recommendation));
        setClarification(readClarification(value.clarification));
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
  const composed = draft?.source.kind === "catalogue_composed";
  const qualified = draft?.guided_experiment === "qualified_dutch_grid";
  const guided = draft?.template_key === "dutch" && !!draft.design.input_policy;
  const seedSchema = draft?.design.input_policy?.json_schema.properties as Record<string, { enum?: number[] }> | undefined;
  const seedChoices = seedSchema?.seed?.enum;

  if (!config || loadingDraft) return <div className="ai-page"><h1>Design with AI</h1>{error ? <div role="alert">{error} <button onClick={() => void initialize()}>Retry</button></div> : <p>Loading design workspace…</p>}</div>;
  if (!config.enabled) return <div className="ai-page"><h1>Design with AI</h1><div className="card ai-disabled"><Sparkles /><h2>The AI design pilot is not enabled</h2><p>Your administrator can enable it in a private development or staging environment.</p><Link href="/builder">Open Build Solution <ArrowRight size={15} /></Link></div></div>;

  const selectedNode = preview?.nodes.find(node => node.id === selectedId);
  const selectedReview = selectedNode ? nodeReview(selectedNode) : null;
  const stage = designStage(draft);
  const validation = draft?.pending && showProposed ? draft.pending.validation : draft?.validation;
  const availableTemplates = templates.filter(item => item.available);
  const reviewServices = (draft?.pending?.design.nodes || preview?.nodes || []).filter(node => node.data.service);
  const examples = supportedExamples(draft?.design.editing_scope, chatEnabled, !!draft);
  function selectNode(id: string, origin?: HTMLElement) {
    selectionOrigin.current = origin || null; if (draft?.pending && !preview?.nodes.some(node=>node.id===id)) setShowProposed(true); setSelectedId(id); chooseArea("canvas");
  }
  function closeSelection() { setSelectedId(null); selectionOrigin.current?.focus(); }
  return <div className="ai-page ai-studio">
    <header className="ai-toolbar">
      <div className="ai-workspace-name"><Sparkles size={19}/><div><h1>Design with AI</h1><p title={draft?.design.name}>{draft?.design.name || "New workflow"}</p></div><span className={`ai-stage ${stage.startsWith("Applied") ? "applied" : stage.toLowerCase()}`} role="status">{stage}</span></div>
      <div className="ai-toolbar-actions">
        <button disabled={!!busy} onClick={() => requestSwitch({kind:"conversation",id:crypto.randomUUID()})}>New conversation</button>
        {draft && <><button disabled={!!busy || !draft.can_undo} onClick={() => action("Undoing", async () => {setDraft(await api(`/drafts/${draft.id}/undo`, {revision:draft.revision}));setShowProposed(false);setSelectedId(null);})}><Undo2 size={15}/>Undo</button>
          <button className="ai-primary" disabled={!!busy || !!draft.pending || !draft.dirty || !draft.validation.valid} onClick={() => action("Saving",async () => {const value=await api(`/drafts/${draft.id}/save`,{revision:draft.revision});setDraft(value.draft);setActivity(current=>[...current,...value.activity].slice(-60));})}><Save size={15}/>Save draft</button>
          {draft.saved_solution_id && !draft.dirty && <Link href={`/builder?solutionId=${encodeURIComponent(draft.saved_solution_id)}`}>Advanced Builder <ArrowRight size={13}/></Link>}
        </>}
        <button onClick={() => setTechnical(true)}>Technical details</button>
      </div>
    </header>
    {config.pilot_notice && <p className="ai-muted" role="status">{config.pilot_notice}</p>}
    <div className="ai-workspace-status">
      {config.provider_mode === "test" ? <span>Prepared synthetic proposal. No live AI or execution.</span> : <span>{composed ? "Design only · execution unavailable" : "Saving does not execute a workflow"}</span>}
      <span>{composed ? "Runtime unverified" : !chatEnabled ? allowancePaused ? "AI messages paused" : "AI disconnected" : "Manual AI messages enabled"}</span>
    </div>
    {switchTarget && <div className="ai-alert" role="alert"><span>Unsaved work and the pending proposal will remain available to resume.</span><button onClick={()=>setSwitchTarget(null)}>Stay here</button><button onClick={()=>void navigate(switchTarget)}>Continue</button></div>}
    {error && <div className="ai-alert" role="alert">{error}<button onClick={()=>draft ? action("Refreshing",async()=>setDraft(await api(`/drafts/${draft.id}`))) : initialize()}>Refresh</button>{retryPrompt && <button disabled={!!busy || !chatEnabled} onClick={()=>send(retryPrompt,true)}>Retry request</button>}</div>}
    <div className="ai-mobile-tabs" role="tablist" aria-label="Workspace areas" onKeyDown={event=>{if(["ArrowLeft","ArrowRight","Home","End"].includes(event.key)){event.preventDefault();const next=nextWorkspaceArea(area,event.key);chooseArea(next);document.getElementById(`tab-${next}`)?.focus();}}}>{(["library","canvas","assistant"] as const).map(item=><button key={item} id={`tab-${item}`} role="tab" tabIndex={area===item?0:-1} aria-selected={area===item} aria-controls={`area-${item}`} onClick={()=>chooseArea(item)}>{item==="canvas"?"Workflow":item==="library"?"Library":"Assistant"}</button>)}</div>
    <div className="ai-workspace">
      <aside className="ai-panel ai-library ai-area" id="area-library" data-active={area==="library"} aria-label="Authorised library">
        <div className="ai-panel-title">Catalogue & library <span className="ai-count">{reviewServices.length || recommendation?.steps.length || availableTemplates.length}</span></div>
        <div className="ai-library-scroll">
          <h2>In this review</h2>
          {reviewServices.length ? reviewServices.map((node,index)=>{const info=nodeReview(node);return <button className="ai-catalogue-card" key={node.id} onClick={event=>selectNode(node.id,event.currentTarget)}><span className="ai-step-number">{index+1}</span><strong>{info.title}</strong><small>{info.purpose}</small><span>Inspect step</span></button>;}) : recommendation?.steps.length ? recommendation.steps.map((step,index)=><article className="ai-catalogue-card" key={index}><strong>{step.title}</strong><small>{recommendation.composition_review?.steps[index]?.purpose || "Declared capability in this recommendation"}</small></article>) : <p className="ai-muted">No workflow selected. Review a recommendation or an available creation path.</p>}
          {availableTemplates.length > 0 && <><h2>Available creation paths</h2>{availableTemplates.map(item=><button className="ai-catalogue-card" key={item.key} disabled={!!busy} onClick={()=>start(item.key)}><strong>{item.label}</strong><small>{item.description || "Create a separate reviewable copy"}</small><span>Create a separate copy</span></button>)}</>}
          <details className="ai-resume"><summary>Resume ({resumeDrafts.length})</summary>{resumeDrafts.map(item=><article key={item.id}><strong>{item.name}</strong><small>{item.pending_changes ? "Proposal pending" : item.dirty ? "Unsaved" : "Saved"}</small><button disabled={!!busy || item.id===draft?.id} aria-label={`Resume ${item.name} ${item.id.slice(0,8)}`} onClick={()=>requestSwitch({kind:"resume",id:item.id})}>{item.id===draft?.id?"Open":"Resume"}</button></article>)}</details>
          {draft && <button className="ai-start-over" disabled={!!busy} onClick={()=>requestSwitch({kind:"home"})}>Choose another design</button>}
          <p className="ai-muted">Additions require a supported proposal. Catalogue metadata does not establish live availability.</p>
        </div>
      </aside>
      <section className="ai-panel ai-workflow ai-area" id="area-canvas" data-active={area==="canvas"} aria-label="Workflow preview">
        <div className="ai-panel-title"><h2>Workflow</h2><span className="ai-tag">{draft?.pending && showProposed ? "Proposed · not applied" : draft ? `${draft.design.nodes.length} applied steps` : "No design created"}</span></div>
        {draft?.pending && <div className="ai-preview-switch"><span>{showProposed?"Previewing the proposal":"Current applied design"}</span><button aria-pressed={!showProposed} onClick={()=>setShowProposed(value=>!value)}>{showProposed?"View current":"Preview proposal"}</button></div>}
        <div className="ai-canvas" data-preview={draft?.pending && showProposed ? "proposed":"current"}>
          {nodes.length ? <ReactFlow key={`${draft?.id}:${draft?.revision}:${showProposed}`} nodes={nodes.map(node=>({...node,selected:node.id===selectedId}))} edges={preview?.edges || []} fitView fitViewOptions={{padding:.18,minZoom:.5,maxZoom:1}} nodesDraggable={false} nodesConnectable={false} elementsSelectable deleteKeyCode={null} minZoom={.25} maxZoom={1.4} onNodeClick={(event,node)=>selectNode(node.id,event.currentTarget as HTMLElement)} aria-label="Active experiment workflow"><WorkspaceViewport/><Background gap={20} color="#e1ddec"/><Controls showInteractive={false}/></ReactFlow> : <div className="ai-empty-workflow"><Sparkles size={30}/><h2>{draft?.pending?"Empty applied design":"Your workflow starts here"}</h2><p>{draft?.pending?"The proposal is preserved. Apply it from the assistant when you are ready.":"Review a supported recommendation in the assistant before creating a design."}</p>{draftId && !draft && <p role="alert">This draft could not be opened. Your other work is unchanged.</p>}</div>}
          {selectedReview && selectedNode && <section className="ai-node-inspector" aria-labelledby="selected-step-title" onKeyDown={event=>{if(event.key==="Escape")closeSelection();}}><div className="ai-inspector-heading"><h3 id="selected-step-title" ref={inspectorHeading} tabIndex={-1}>{selectedReview.title}</h3><button aria-label="Close step settings" onClick={closeSelection}><X size={16}/></button></div><p>{selectedReview.purpose}</p><h4>{draft?.pending && showProposed?"Proposed settings":"Applied settings"}</h4>
            <dl>{Object.entries(selectedReview.settings).map(([key,value])=><div key={key}><dt>{key}</dt><dd>{String(value)}</dd></div>)}</dl>{!Object.keys(selectedReview.settings).length && <p className="ai-muted">No instance parameters declared.</p>}
            {draft?.instance_settings?.find(item=>item.node_id===selectedNode.id)?.limitation && <p role="alert">{draft.instance_settings.find(item=>item.node_id===selectedNode.id)?.limitation}</p>}
            <details><summary>Technical details</summary><p>Instance <code>{selectedNode.id}</code></p><pre>{JSON.stringify({pin:selectedNode.data.operation_contract,configuration:selectedNode.data.configuration},null,2)}</pre></details>
          </section>}
        </div>
        <div className="ai-canvas-footer"><span>{draft?.pending?"Review pending · Apply changes the draft only":draft?.saved_solution_id && !draft.dirty?"Saved design · no execution implied":"Design view · nothing executes here"}</span><span>{selectedNode?"Escape closes settings":"Select a step to inspect settings"}</span></div>
        {!!validation?.errors.length && <div className="ai-required" role="alert">{validation.errors.map((message,index)=><p key={index}>{message}</p>)}</div>}
        {!!validation?.required_inputs.some(input=>input.resolution!=="verified") && <div className="ai-required">{validation.required_inputs.filter(input=>input.resolution!=="verified").map((input,index)=><p key={index}>Required: {input.operation} / {input.name} · {input.resolution}</p>)}</div>}
         {draft && (qualified || guided || draft.design.input_policy) && <details className="ai-legacy-settings"><summary>Supported input settings</summary>          {qualified ? <div className="ai-guided-settings"><strong>Current applied seed: {String(appliedSeed(draft) ?? "unavailable")}</strong><p>Review a supported seed change here. It creates a proposal without another AI request or execution.</p><label htmlFor="qualified-grid-seed">Grid seed</label><select id="qualified-grid-seed" value={seed} onChange={event => setSeed(event.target.value)}><option value="42">42</option><option value="43">43</option></select><button disabled={!!busy || !!draft.pending || Number(seed) === appliedSeed(draft)} onClick={() => action("Reviewing settings", async () => {setDraft(await api(`/drafts/${draft.id}/guided-settings`, {revision: draft.revision, seed: Number(seed)})); setShowProposed(true);})}>Review seed change</button><p>Apply changes, Undo or Save remain separate actions. Saving does not execute the workflow.</p></div> : guided ? <div className="ai-guided-settings"><strong>Settings: seed {String(draft.design.run_input?.seed ?? "not set")}</strong><p>{draft.dirty ? "Save your draft, then review and check readiness in Build Solution." : "Your saved settings are ready to review in Build Solution."}</p><details><summary>Advanced settings (optional)</summary><label htmlFor="grid-seed">Grid seed</label>{seedChoices ? <select id="grid-seed" value={seed} onChange={event => setSeed(event.target.value)}>{seedChoices.map(value => <option key={value} value={value}>{value}</option>)}</select> : <input id="grid-seed" type="number" step="1" value={seed} onChange={event => setSeed(event.target.value)} />}<p>The seed controls the generator's random choices. Only settings accepted by the approved wrapper are supported.</p><button disabled={!!busy || !seed.trim() || !Number.isSafeInteger(Number(seed)) || Number(seed) === draft.design.run_input?.seed} onClick={() => action("Reviewing settings", async () => { setDraft(await api(`/drafts/${draft.id}/guided-settings`, { revision: draft.revision, seed: Number(seed) })); setShowProposed(true); })}>Review seed change</button><p>Review the proposal above, select Apply changes, then Save draft. Undo restores the previous applied settings.</p></details></div> : draft.design.input_policy && <details className="ai-validation"><summary>Supported run input</summary><pre>{JSON.stringify(draft.design.run_input, null, 2)}</pre><p>Wrapper schema evidence: {draft.design.input_policy.evidence_reference}</p></details>}
</details>}
        {qualified && draft && <details className="ai-qualified"><summary>Registered experiment readiness and execution</summary><ExperimentExecution draftId={draft.id} revision={draft.revision} saved={!!draft.saved_solution_id && !draft.dirty && !draft.pending}/></details>}
      </section>
      <section className="ai-panel ai-conversation ai-area" id="area-assistant" data-active={area==="assistant"} aria-label="Design conversation">
        <div className="ai-panel-title"><h2><Sparkles size={16}/>Assistant</h2><span className="ai-tag">{config.provider_mode==="test"?"Prepared fixture":config.provider_name || "AI"}</span></div>
        <div className="ai-chat-history" role="log" aria-live="polite">{!messages.length && <div className="ai-chat-welcome"><h3>{draft?"Review this design":"What would you like to explore?"}</h3><p>{config.provider_mode==="test"?"Use the prepared proposal and explicit controls. Chat is disabled.":"Describe your objective. Nothing changes until you review and apply a supported proposal."}</p></div>}{messages.map((message,index)=><div className={`ai-message ${message.role}`} key={index}><small>{message.role==="user"?"You":"Assistant"}</small>{message.role==="assistant"?<ConversationMessage content={message.content}/>:<p>{message.content}</p>}</div>)}{busy && <p className="ai-thinking"><LoaderCircle size={14} className="ai-spin"/>{busy}…</p>}<div ref={chatEnd}/></div>
        {!draft && recommendation && <DiscoveryRecommendation compact recommendation={recommendation} busy={!!busy} onCreate={()=>{chooseArea("assistant");requestSwitch({kind:"start",key:recommendation.key || "",carryDiscovery:true});}}/>}
        {draft?.pending && <section className="ai-proposal" aria-label="Proposed changes"><strong>Proposed changes</strong><div className="ai-review-body">{draft.pending.composition_review?<CompositionReview compact review={draft.pending.composition_review}/>:draft.pending.structural_review?<StructuralReview review={draft.pending.structural_review}/>:draft.pending.parameter_review?.changes.length?<InstanceSettingReview review={draft.pending.parameter_review}/>:<ul>{draft.pending.turn.edits.map((edit,index)=><li key={index}>{edit.kind.replaceAll("_"," ")}: {edit.value}</li>)}</ul>}{!draft.pending.validation.valid && <p role="alert">{draft.pending.validation.errors.join(" ")}</p>}</div><button className="ai-primary" disabled={!!busy || !draft.pending.validation.valid} onClick={()=>action("Applying",async()=>{setDraft(await api(`/drafts/${draft.id}/apply`,{revision:draft.revision,proposal_id:draft.pending!.id}));setMessages(current=>[...current,{role:"assistant",content:"Changes applied to the draft. Save when ready; no workflow executed."}]);})}>Apply changes</button></section>}
        {conversationWarning && <p className="ai-conversation-warning" role="status">{conversationWarning}</p>}
        <div className="ai-examples">{examples.map(example=><button key={example} disabled={!!busy} onClick={()=>setPrompt(example)}>{example}<ArrowRight size={13}/></button>)}</div>
        <form className="ai-composer" onSubmit={event=>{event.preventDefault();void send();}}><label htmlFor="design-prompt" className="ai-sr-only">Describe your objective or request a change</label><textarea id="design-prompt" value={prompt} maxLength={4000} rows={2} disabled={!!busy} onChange={event=>setPrompt(event.target.value)} placeholder={promptPlaceholder(config.provider_mode==="test",chatEnabled,allowancePaused)}/><div><small>{!chatEnabled?allowance?.message || (config.provider_mode==="test"?"No live AI. Use the review controls.":"AI disconnected. Existing controls remain available."):"Review before Apply. Each Send uses a manual AI message."}</small>{busy==="Thinking"?<button type="button" onClick={()=>controller.current?.abort()}>Cancel</button>:<button className="ai-primary" aria-label="Send request" disabled={!!busy || !prompt.trim() || !chatEnabled}><Send size={16}/></button>}</div></form>
      </section>
    </div>
    <ReviewDialog open={technical} onClose={()=>setTechnical(false)} title="Workspace technical details"><p>{historyUnavailable?"Earlier conversation history is unavailable; it has not been reconstructed.":"Conversation belongs to this account and selected draft."}</p>{draft && <><p>Draft <code>{draft.id}</code> · revision {draft.revision}</p><p>Source <code>{draft.source.revision}</code></p><p>{draft.reference_note}</p><pre>{JSON.stringify(draft.validation,null,2)}</pre></>}{allowance && <><p>{allowance.message}</p><pre>{JSON.stringify(allowance,null,2)}</pre><button onClick={()=>void refreshAllowance()}>Check allowance</button></>}<p>Runtime model: {config.model || "No provider connected"}</p><h3>Tool events</h3><ol>{activity.map((event,index)=><li key={index}><code>{event.tool}</code> · {event.status}: {event.summary}</li>)}</ol>{templates.filter(item=>!item.available).map(item=><p key={item.key}>{item.label}: {item.reason || "Unavailable"}</p>)}</ReviewDialog>
  </div>;
}
