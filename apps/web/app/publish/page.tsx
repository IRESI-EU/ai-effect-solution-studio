"use client";

import Link from "next/link";
import {
  ArrowLeft, ArrowRight, Box, Check, CircleAlert, FileCode2, FolderGit2, GitBranch, Lightbulb, Package, Upload,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { nodeLabels, useAuth, type NodeCode } from "../../components/auth-context";
import { ServiceRuntimeManager, type ManagedRuntimeService } from "../../components/service-runtime-manager";
import {
  emptyGuidedForm,
  formFromExample,
  formFromManifest,
  mergeManifest,
  parseProtoOperations,
  slugify,
  type GuidedServiceForm,
  type ProtoOperation,
} from "./guided-manifest";
import { PackageImportPanel } from "./package-import";
import { AskHelper, DraftHelper, ExplainHelper, useHelperStatus } from "./ai-helper";
import { emptyRow, toDefinition, toRows, type SettingRow } from "../../components/service-settings-editor";
import type { SettingsDefinition } from "../../components/node-settings";
import { ConnectStep, DescribeStep, ReviewStep, TextField, type CatalogueEntry, type ConnectionResult, type PreviewResponse, type RuntimeChoice, type Evidence } from "./wizard-steps";
import { workshopExamples, type WorkshopExample } from "./workshop-examples";

type Source = "package" | "git" | "container" | "unpackaged";
type Step = "start" | "describe" | "connect" | "review" | "done";

type Draft = {
  source: Source | null;
  step: Step;
  form: GuidedServiceForm;
  base: Record<string, unknown> | null;
  origin: { kind: "git" | "file" | "example" | "form"; label: string; repo?: string; branch?: string; path?: string };
  idEdited: boolean;
  settingsChannel: SettingsDefinition["channel"];
  settingsRows: SettingRow[];
};

const DRAFT_KEY = "publish.draft.v2";
const STEPS: { key: Step; label: string; hint: string }[] = [
  { key: "start", label: "Start", hint: "What do you have?" },
  { key: "describe", label: "Describe", hint: "What it does and where it fits" },
  { key: "connect", label: "Connect", hint: "How the platform calls it" },
  { key: "review", label: "Review", hint: "Check and submit" },
];

const newDraft = (): Draft => ({
  source: null, step: "start", form: { ...emptyGuidedForm }, base: null, origin: { kind: "form", label: "Form" }, idEdited: false,
  settingsChannel: "parameters", settingsRows: [],
});
const initialEvidence: Evidence = { revisionPinned: false, imageReviewed: false, secretsExternal: false, healthVerified: false };

export default function PublishServicePage() {
  const { user } = useAuth();
  const [draft, setDraft] = useState<Draft>(newDraft);
  const [restored, setRestored] = useState(false);
  const [catalogue, setCatalogue] = useState<CatalogueEntry[]>([]);
  const [managedServices, setManagedServices] = useState<ManagedRuntimeService[]>([]);
  const [protoOperations, setProtoOperations] = useState<ProtoOperation[]>([]);
  const [git, setGit] = useState({ repo: "", branch: "main", path: "ai-effect.service.json" });
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [runtime, setRuntime] = useState<RuntimeChoice>("unsure");
  const [evidence, setEvidence] = useState<Evidence>(initialEvidence);
  const [acknowledged, setAcknowledged] = useState(false);
  const [submitted, setSubmitted] = useState<{ name: string; id: string } | null>(null);
  const [connection, setConnection] = useState<ConnectionResult | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const helper = useHelperStatus();

  const nodeCode = (user?.node || null) as NodeCode | null;
  const nodeLabel = nodeCode ? nodeLabels[nodeCode] : null;
  const form = draft.form;

  // Restore an unfinished draft from this browser.
  useEffect(() => {
    try {
      const saved = localStorage.getItem(DRAFT_KEY);
      if (saved) {
        const parsed = JSON.parse(saved) as Draft;
        if (parsed?.form && parsed.step !== "done" && parsed.step !== "start") {
          setDraft({ ...newDraft(), ...parsed, form: { ...emptyGuidedForm, ...parsed.form } });
          setRestored(true);
        }
      }
    } catch { /* no saved draft */ }
  }, []);
  useEffect(() => {
    try {
      if (draft.step === "start" || draft.step === "done") localStorage.removeItem(DRAFT_KEY);
      else localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
    } catch { /* storage unavailable */ }
  }, [draft]);

  async function loadServices() {
    const response = await fetch("/api/services?include_archived=true", { cache: "no-store" }).catch(() => null);
    if (!response?.ok) return;
    const data = await response.json();
    if (!Array.isArray(data)) return;
    setCatalogue(data);
    if (user && ["node_manager", "platform_admin"].includes(user.role)) setManagedServices(data);
  }
  useEffect(() => { void loadServices(); }, [user?.id]);

  // Provider defaults to the person's node.
  useEffect(() => {
    if (nodeLabel && !draft.form.provider) update("provider", `AI-EFFECT ${nodeLabel}`);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodeLabel, draft.step]);

  function update<K extends keyof GuidedServiceForm>(key: K, value: GuidedServiceForm[K]) {
    setDraft((current) => {
      const next = { ...current.form, [key]: value };
      // Keep the ID in step with the name until someone edits it.
      if (key === "name" && !current.idEdited) next.serviceId = suggestedId(String(value), nodeCode);
      if (key === "containerName" && (!current.form.internalHost || current.form.internalHost === current.form.containerName)) {
        next.internalHost = String(value);
      }
      return { ...current, form: next, idEdited: current.idEdited || key === "serviceId" };
    });
    if (["containerName", "internalHost", "internalPort", "healthPath"].includes(key)) setConnection(null);
    setPreview(null);
    setAcknowledged(false);
  }

  function setSettings(patch: Partial<Pick<Draft, "settingsChannel" | "settingsRows">>) {
    setDraft((current) => ({ ...current, ...patch }));
    setPreview(null);
    setAcknowledged(false);
  }

  async function testConnection() {
    setBusy("connection");
    setConnection(null);
    try {
      const response = await fetch("/api/services/runtime-check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          internal_host: form.internalHost.trim() || form.containerName.trim(),
          internal_port: form.internalPort.trim() || "8080",
          health_path: form.healthPath.trim() || "/health",
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(apiError(data?.detail) || "The connection could not be tested.");
      setConnection(data);
      if (data.status === "ready") setEvidence((current) => ({ ...current, healthVerified: true }));
    } catch (caught) {
      setConnection({ status: "unavailable", message: caught instanceof Error ? caught.message : "The connection could not be tested.", recommended_action: "", runtime_url: null });
    } finally {
      setBusy(null);
    }
  }

  function goTo(step: Step) {
    setError(null);
    setDraft((current) => ({ ...current, step }));
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function startOver() {
    setDraft(newDraft());
    setPreview(null);
    setSubmitted(null);
    setAcknowledged(false);
    setEvidence(initialEvidence);
    setRuntime("unsure");
    setProtoOperations([]);
    setConnection(null);
    setRestored(false);
    setError(null);
  }

  function choose(source: Source) {
    setError(null);
    setDraft((current) => ({ ...current, source }));
  }

  function startForm(origin: Draft["origin"], form: GuidedServiceForm, base: Record<string, unknown> | null) {
    const declared = base?.settings as SettingsDefinition | undefined;
    const rows = declared?.schema?.properties ? toRows(declared) : [];
    setDraft({
      source: draft.source || "container", step: "describe", form, base, origin, idEdited: Boolean(form.serviceId),
      settingsChannel: declared?.channel || "parameters", settingsRows: rows,
    });
    setConnection(null);
    setPreview(null);
  }

  async function readGitManifest() {
    setBusy("git");
    setError(null);
    try {
      const response = await fetch("/api/services/import/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_url: git.repo.trim(), branch: git.branch.trim(), manifest_path: git.path.trim() }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(apiError(data?.detail) || "The manifest could not be read from that repository.");
      const manifestFound = data?.raw_manifest && Object.keys(data.raw_manifest).length > 0;
      if (!manifestFound) {
        const reasons = (data?.validation || []).filter((item: { level: string }) => item.level === "error").map((item: { message: string }) => item.message);
        throw new Error(reasons.join(" ") || "No service manifest was found at that location.");
      }
      startForm(
        { kind: "git", label: `${git.repo.trim()} @ ${git.branch.trim()}`, repo: git.repo.trim(), branch: git.branch.trim(), path: git.path.trim() },
        { ...formFromManifest(data.raw_manifest), sourceReference: git.repo.trim(), sourceRevision: git.branch.trim() },
        data.raw_manifest,
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The manifest could not be read.");
    } finally {
      setBusy(null);
    }
  }

  async function readFile(file: File) {
    setError(null);
    const name = file.name.toLowerCase();
    if (name.endsWith(".zip")) {
      choose("package");
      setError("ZIP packages are reviewed on their own screen: choose “A service package (ZIP)”.");
      return;
    }
    const text = await file.text();
    if (name.endsWith(".proto")) {
      const operations = parseProtoOperations(text);
      if (!operations.length) {
        setError(`No rpc operations were found in ${file.name}.`);
        return;
      }
      setProtoOperations(operations);
      const first = operations[0];
      startForm(
        { kind: "file", label: file.name },
        {
          ...form,
          interfaceType: "grpc",
          protoUri: file.name,
          contractUri: file.name,
          operationName: first.name,
          inputMessageName: first.input,
          outputMessageName: first.output,
          grpcInputMessage: first.input,
          grpcOutputMessage: first.output,
        },
        draft.base,
      );
      return;
    }
    try {
      const manifest = JSON.parse(text) as Record<string, unknown>;
      startForm({ kind: "file", label: file.name }, formFromManifest(manifest), manifest);
    } catch {
      setError(`${file.name} is not valid JSON. Drop an AI-EFFECT service manifest (.json) or a gRPC contract (.proto).`);
    }
  }

  function startFromExample(example: WorkshopExample) {
    startForm(
      { kind: "example", label: `${example.country} example (${example.service})` },
      { ...formFromExample(example.manifest), provider: nodeLabel ? `AI-EFFECT ${nodeLabel}` : "" },
      null,
    );
  }

  const settingsResult = useMemo(() => {
    if (!draft.settingsRows.length) return { definition: null as SettingsDefinition | null, error: null as string | null };
    try {
      return { definition: toDefinition(draft.settingsChannel, draft.settingsRows), error: null };
    } catch (caught) {
      return { definition: null, error: caught instanceof Error ? caught.message : "Check the settings." };
    }
  }, [draft.settingsChannel, draft.settingsRows]);

  const manifest = useMemo(() => {
    const merged = mergeManifest(draft.base, form);
    if (settingsResult.definition) merged.settings = settingsResult.definition;
    else delete merged.settings;
    return merged;
  }, [draft.base, form, settingsResult]);

  async function checkWithPlatform() {
    setBusy("check");
    setError(null);
    try {
      const response = await fetch("/api/services/import/preview-manual", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(sourceFields(draft, form, manifest)),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(apiError(data?.detail) || "The platform could not check this service.");
      setPreview(data);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The platform could not check this service.");
    } finally {
      setBusy(null);
    }
  }

  useEffect(() => {
    if (draft.step === "review" && !preview && busy !== "check") void checkWithPlatform();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft.step]);

  async function submit() {
    if (!preview || preview.status === "invalid" || !acknowledged) return;
    setBusy("submit");
    setError(null);
    try {
      const response = await fetch("/api/services/import/confirm-manual", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...sourceFields(draft, form, preview.raw_manifest),
          onboarding: {
            source_type: draft.origin.kind === "git" ? "public_git" : "manual_manifest",
            source_revision: form.sourceRevision || null,
            runtime_status: runtime === "already_running" ? "already_running" : "needs_deployment",
            revision_pinned: evidence.revisionPinned,
            image_reviewed: evidence.imageReviewed,
            secrets_external: evidence.secretsExternal,
            health_verified: evidence.healthVerified,
            registration_only_acknowledged: acknowledged,
          },
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(apiError(data?.detail) || "Submission failed.");
      setSubmitted({ name: data.name || form.name, id: data.id || form.serviceId });
      setDraft((current) => ({ ...current, step: "done" }));
      void loadServices();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Submission failed.");
    } finally {
      setBusy(null);
    }
  }

  const describeMissing = [!form.name.trim() && "a name", !form.description.trim() && "what it does", !form.provider.trim() && "the provider", !form.category.trim() && "a category", !form.inputType.trim() && "what it takes", !form.outputType.trim() && "what it produces"].filter(Boolean) as string[];
  const connectMissing = [
    !form.containerName.trim() && "the container name",
    !form.operationName.trim() && "the operation",
    !form.image.trim() && !form.dockerfile.trim() && "a Docker image",
    settingsResult.error && "valid settings",
  ].filter(Boolean) as string[];
  const stepIndex = STEPS.findIndex((step) => step.key === draft.step);
  const packageMode = draft.source === "package" && draft.step === "start";

  return (
    <main className="page publish-page publish-wizard">
      <header className="page-header">
        <div className="page-header__text">
          <h1 className="page-header__title">Add a service</h1>
          <p className="page-header__lead">
            Put your service in the AI-EFFECT catalogue so others can use it in their workflows. It takes a few minutes; an administrator reviews it before it appears.
          </p>
        </div>
        <div className="page-header__actions">
          <Link href="/catalogue" className="ae-btn ae-btn--secondary">View catalogue</Link>
          {user?.role === "platform_admin" && <Link href="/admin" className="ae-btn ae-btn--secondary">Review submissions</Link>}
        </div>
      </header>

      {draft.step !== "done" && !packageMode && (
        <ol className="wizard-steps" aria-label="Steps">
          {STEPS.map((step, index) => (
            <li key={step.key} className={index === stepIndex ? "is-current" : index < stepIndex ? "is-done" : ""} aria-current={index === stepIndex ? "step" : undefined}>
              <span className="wizard-steps__dot">{index < stepIndex ? <Check size={14} aria-hidden="true" /> : index + 1}</span>
              <span><strong>{step.label}</strong><small>{step.hint}</small></span>
            </li>
          ))}
        </ol>
      )}

      {restored && draft.step !== "done" && (
        <div className="ae-alert wizard-restored" role="status">
          <span>We kept your unfinished service <strong>{form.name || "draft"}</strong> from last time.</span>
          <button type="button" className="ae-btn ae-btn--secondary" onClick={startOver}>Start a new one</button>
        </div>
      )}

      {draft.step === "start" && (
        <section className="wizard-card">
          <h2 className="wizard-card__title">What do you have?</h2>
          <p className="wizard-card__lead">Pick the closest match. You can change details on the next screens.</p>
          <div className="source-grid">
            <SourceCard icon={Package} title="A service package (ZIP)" text="An AI4EU / WP3 export with blueprint.json, dockerinfo.json and .proto files. Everything is filled in for you." active={draft.source === "package"} onClick={() => choose("package")} badge="Fastest" />
            <SourceCard icon={FolderGit2} title="A GitHub repository" text="A public repository with an AI-EFFECT service manifest (ai-effect.service.json)." active={draft.source === "git"} onClick={() => choose("git")} />
            <SourceCard icon={Box} title="A Docker image or running container" text="Answer a few questions about the service and how it is called." active={draft.source === "container"} onClick={() => choose("container")} />
            <SourceCard icon={Lightbulb} title="It isn't packaged yet" text="See what a service needs before it can join the platform, and save a draft." active={draft.source === "unpackaged"} onClick={() => choose("unpackaged")} />
          </div>

          {draft.source === "package" && <div className="wizard-panel"><PackageImportPanel /></div>}

          {draft.source === "git" && (
            <div className="wizard-panel">
              <div className="wizard-grid">
                <TextField label="Repository URL" value={git.repo} onChange={(repo) => setGit({ ...git, repo })} placeholder="https://github.com/your-org/your-service" wide />
                <TextField label="Branch, tag or commit" value={git.branch} onChange={(branch) => setGit({ ...git, branch })} hint="A tag or commit keeps the reviewed version fixed." />
                <TextField label="Manifest file" value={git.path} onChange={(path) => setGit({ ...git, path })} />
              </div>
              <button type="button" className="ae-btn ae-btn--primary" disabled={!git.repo.trim() || busy === "git"} onClick={readGitManifest}>
                {busy === "git" ? "Reading the manifest…" : "Read the manifest"} <ArrowRight size={16} aria-hidden="true" />
              </button>
            </div>
          )}

          {draft.source === "container" && (
            <div className="wizard-panel">
              <p>You will describe the service, then say how the platform calls it. Have the Docker image name and the port at hand.</p>
              <button type="button" className="ae-btn ae-btn--primary" onClick={() => startForm({ kind: "form", label: "Form" }, { ...emptyGuidedForm, provider: nodeLabel ? `AI-EFFECT ${nodeLabel}` : "" }, null)}>
                Start <ArrowRight size={16} aria-hidden="true" />
              </button>
            </div>
          )}

          {draft.source === "unpackaged" && (
            <div className="wizard-panel">
              <p>To run on the platform, a service needs:</p>
              <ul className="wizard-checklist">
                <li><Check size={15} aria-hidden="true" /> <span><strong>A Docker image</strong>, built from your code, that starts on its own.</span></li>
                <li><Check size={15} aria-hidden="true" /> <span><strong>A way to be called</strong>: the AI-EFFECT control interface (<code>/control/execute</code>), a gRPC contract (<code>.proto</code>), or a REST endpoint behind an adapter.</span></li>
                <li><Check size={15} aria-hidden="true" /> <span><strong>A health check</strong> (for example <code>GET /health</code>) so the platform can see it is up.</span></li>
                <li><Check size={15} aria-hidden="true" /> <span><strong>Clear inputs and outputs</strong>: what data it takes and what it produces.</span></li>
              </ul>
              <p className="muted">The service onboarding guide and the node examples below show working services. You can also describe your service now and finish the technical part later.</p>
              <button type="button" className="ae-btn ae-btn--secondary" onClick={() => startForm({ kind: "form", label: "Form" }, { ...emptyGuidedForm, provider: nodeLabel ? `AI-EFFECT ${nodeLabel}` : "" }, null)}>
                Describe it now <ArrowRight size={16} aria-hidden="true" />
              </button>
            </div>
          )}

          <div
            className="drop-zone"
            onDragOver={(event) => { event.preventDefault(); }}
            onDrop={(event) => { event.preventDefault(); const file = event.dataTransfer.files?.[0]; if (file) void readFile(file); }}
          >
            <Upload size={20} aria-hidden="true" />
            <div>
              <strong>Already have a manifest (.json) or a gRPC contract (.proto)?</strong>
              <span>Drop it here, or <button type="button" className="link-button" onClick={() => fileInput.current?.click()}>choose a file</button>, and the form is filled in for you.</span>
            </div>
            <input ref={fileInput} type="file" accept=".json,.proto,application/json" hidden onChange={(event) => { const file = event.target.files?.[0]; if (file) void readFile(file); event.target.value = ""; }} />
          </div>

          <div className="example-row">
            <span>Or start from a node&apos;s example:</span>
            {workshopExamples.map((example) => (
              <button key={example.key} type="button" className="example-chip" onClick={() => startFromExample(example)}>
                {example.country} · {example.service}
              </button>
            ))}
          </div>
          {error && <p className="wizard-error" role="alert"><CircleAlert size={16} aria-hidden="true" /> {error}</p>}
        </section>
      )}

      {draft.step === "describe" && (
        <section className="wizard-card">
          <SourceNote origin={draft.origin} />
          <DescribeStep
            form={form}
            update={update}
            catalogue={catalogue}
            nodeLabel={nodeLabel}
            isExample={draft.origin.kind === "example"}
            aiSlot={
              <DraftHelper
                status={helper}
                context={{
                  name: form.name,
                  description: form.description,
                  operations: protoOperations.length ? protoOperations.map((op) => `${op.name} (${op.input} -> ${op.output})`).join(", ") : form.operationName,
                  interface: form.interfaceType,
                }}
                onUse={(patch) => {
                  if (patch.description !== undefined) update("description", patch.description);
                  if (patch.use_when !== undefined) update("useWhen", patch.use_when);
                  if (patch.category !== undefined) update("category", patch.category);
                }}
              />
            }
          />
          <WizardNav onBack={() => goTo("start")} onNext={() => goTo("connect")} nextDisabled={describeMissing.length > 0} missing={describeMissing} />
        </section>
      )}

      {draft.step === "connect" && (
        <section className="wizard-card">
          <ConnectStep
            form={form}
            update={update}
            protoOperations={protoOperations}
            runtime={runtime}
            onRuntime={setRuntime}
            connection={connection}
            testing={busy === "connection"}
            onTestConnection={testConnection}
            settingsChannel={draft.settingsChannel}
            settingsRows={draft.settingsRows}
            onSettingsChannel={(settingsChannel) => setSettings({ settingsChannel })}
            onSettingsRows={(change) => setDraft((current) => ({ ...current, settingsRows: change(current.settingsRows) }))}
            onAddFirstSetting={() => setSettings({ settingsRows: [emptyRow()] })}
            settingsError={settingsResult.error}
          />
          <WizardNav onBack={() => goTo("describe")} onNext={() => goTo("review")} nextLabel="Review" nextDisabled={connectMissing.length > 0} missing={connectMissing} />
        </section>
      )}

      {draft.step === "review" && (
        <section className="wizard-card">
          <ReviewStep
            form={form}
            nodeLabel={nodeLabel}
            preview={preview}
            checking={busy === "check"}
            onRecheck={checkWithPlatform}
            onEdit={(step) => goTo(step)}
            evidence={evidence}
            onEvidence={(key, value) => setEvidence((current) => ({ ...current, [key]: value }))}
            acknowledged={acknowledged}
            onAcknowledge={setAcknowledged}
            catalogue={catalogue}
            settings={settingsResult.definition}
            connection={connection}
            aiSlot={
              <ExplainHelper
                status={helper}
                messages={(preview?.validation || []).filter((item) => item.level === "error").map((item) => item.message)}
                details={[
                  `Interface: ${form.interfaceType}`, `Operation: ${form.operationName}`,
                  `Container: ${form.containerName}:${form.internalPort}`, `Image: ${form.image || form.dockerfile}`,
                  `Takes: ${form.inputType}`, `Produces: ${form.outputType}`, `Category: ${form.category || "(none)"}`,
                ].join("\n")}
                onGo={(step) => goTo(step)}
              />
            }
          />
          {error && <p className="wizard-error" role="alert"><CircleAlert size={16} aria-hidden="true" /> {error}</p>}
          <div className="wizard-nav">
            <button type="button" className="ae-btn ae-btn--secondary" onClick={() => goTo("connect")}><ArrowLeft size={16} aria-hidden="true" /> Back</button>
            <button type="button" className="ae-btn ae-btn--primary" disabled={!preview || preview.status === "invalid" || !acknowledged || busy === "submit"} onClick={submit}>
              {busy === "submit" ? "Submitting…" : "Submit for review"}
            </button>
          </div>
        </section>
      )}

      {draft.step === "done" && submitted && (
        <section className="wizard-card wizard-done">
          <span className="wizard-done__mark"><Check size={28} aria-hidden="true" /></span>
          <h2 className="wizard-card__title">{submitted.name} is submitted</h2>
          <ol className="wizard-timeline">
            <li className="is-done"><strong>Submitted</strong><span>Saved as a pending service. Nothing was started or deployed.</span></li>
            <li><strong>Administrator review</strong><span>Checks ownership, image, interface and health. You may be asked for missing details.</span></li>
            <li><strong>In the catalogue</strong><span>Once approved, people can find it and use it in the Builder.</span></li>
          </ol>
          <div className="wizard-nav wizard-nav--start">
            <Link href={`/catalogue/${encodeURIComponent(submitted.id)}`} className="ae-btn ae-btn--secondary">Open its catalogue page</Link>
            <button type="button" className="ae-btn ae-btn--primary" onClick={startOver}>Add another service</button>
          </div>
        </section>
      )}

      {["describe", "connect", "review"].includes(draft.step) && <AskHelper status={helper} />}

      {managedServices.length > 0 && (
        <details className="wizard-card wizard-manage">
          <summary>Manage your existing services</summary>
          <p className="muted">Correct the runtime details of services assigned to your node. Saving changes means they are verified again.</p>
          <div style={{ display: "grid", gap: 10 }}>
            {managedServices.map((service) => <ServiceRuntimeManager key={service.id} service={service} onUpdated={loadServices} />)}
          </div>
        </details>
      )}
    </main>
  );
}

function suggestedId(name: string, node: NodeCode | null) {
  const slug = slugify(name);
  if (!slug) return "";
  return node ? `${node}-${slug}` : slug;
}

function sourceFields(draft: Draft, form: GuidedServiceForm, manifest: Record<string, unknown>) {
  return {
    repo_url: draft.origin.repo || form.sourceReference || "provider-supplied",
    branch: draft.origin.branch || form.sourceRevision || "unversioned",
    manifest_path: draft.origin.path || (draft.origin.kind === "file" ? draft.origin.label : "guided/ai-effect.service.json"),
    manifest,
  };
}

function apiError(detail: unknown) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((item) => (typeof item === "object" && item && "msg" in item ? String((item as { msg: unknown }).msg) : String(item))).join(" ");
  return detail ? JSON.stringify(detail) : "";
}

function SourceCard({ icon: Icon, title, text, active, onClick, badge }: { icon: typeof Box; title: string; text: string; active: boolean; onClick: () => void; badge?: string }) {
  return (
    <button type="button" className={`source-card${active ? " is-active" : ""}`} onClick={onClick} aria-pressed={active}>
      <span className="source-card__icon"><Icon size={20} aria-hidden="true" /></span>
      <span className="source-card__title">{title}{badge && <em>{badge}</em>}</span>
      <span className="source-card__text">{text}</span>
    </button>
  );
}

function SourceNote({ origin }: { origin: Draft["origin"] }) {
  if (origin.kind === "form") return null;
  const Icon = origin.kind === "git" ? GitBranch : FileCode2;
  return (
    <p className="source-note">
      <Icon size={15} aria-hidden="true" />
      {origin.kind === "example"
        ? <>Started from the <strong>{origin.label}</strong>. Give your service its own name and description.</>
        : <>Filled in from <strong>{origin.label}</strong>. Check and complete the details.</>}
    </p>
  );
}

function WizardNav({ onBack, onNext, nextLabel = "Next", nextDisabled, missing }: { onBack: () => void; onNext: () => void; nextLabel?: string; nextDisabled?: boolean; missing: string[] }) {
  return (
    <div className="wizard-nav">
      <button type="button" className="ae-btn ae-btn--secondary" onClick={onBack}><ArrowLeft size={16} aria-hidden="true" /> Back</button>
      <span className="wizard-nav__hint">{missing.length ? `Still needed: ${missing.join(", ")}` : ""}</span>
      <button type="button" className="ae-btn ae-btn--primary" onClick={onNext} disabled={nextDisabled}>{nextLabel} <ArrowRight size={16} aria-hidden="true" /></button>
    </div>
  );
}
