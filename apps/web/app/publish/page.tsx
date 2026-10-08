"use client";

import Link from "next/link";
import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { useAuth } from "../../components/auth-context";
import { ServiceRuntimeManager, type ManagedRuntimeService } from "../../components/service-runtime-manager";
import {
  buildGuidedManifest,
  emptyGuidedForm,
  formFromExample,
  type GuidedServiceForm,
  type InterfaceChoice,
} from "./guided-manifest";
import { workshopExamples, type WorkshopExample } from "./workshop-examples";

const API_BASE_URL = "/api";

type EntryMode = "guided" | "git" | "manual";
type RuntimeChoice = "needs_deployment" | "already_running" | "unsure";
type RuntimeEvidence = {
  revisionPinned: boolean;
  imageReviewed: boolean;
  secretsExternal: boolean;
  healthVerified: boolean;
};
type ValidationMessage = { level: "success" | "warning" | "error"; message: string };
type ImportedService = {
  id: string | null;
  name: string;
  provider: string;
  category: string;
  version: string;
  description?: string | null;
  repository_url: string;
  repository_branch: string;
  manifest_path: string;
  interface_type: string;
  orchestration_mode: string;
  adapter_type?: string | null;
  container_name: string;
  internal_host: string;
  image?: string | null;
  dockerfile?: string | null;
  internal_port: string;
  health_path: string;
  input_type?: string | null;
  output_type?: string | null;
  operation_name: string;
  input_message_name?: string | null;
  output_message_name?: string | null;
  proto_uri?: string | null;
  contract_uri?: string | null;
};
type PreviewResponse = {
  status: "valid" | "warning" | "invalid";
  raw_manifest: Record<string, unknown>;
  service: ImportedService | null;
  validation: ValidationMessage[];
};
type ConfirmedService = {
  id: string;
  name: string;
  provider: string;
  category: string;
  trust_badge: string;
  container_name: string;
  operation_name: string;
};

const initialEvidence: RuntimeEvidence = {
  revisionPinned: false,
  imageReviewed: false,
  secretsExternal: false,
  healthVerified: false,
};

export default function PublishServicePage() {
  const { user } = useAuth();
  const [mode, setMode] = useState<EntryMode>("guided");
  const [form, setForm] = useState<GuidedServiceForm>(emptyGuidedForm);
  const [repoUrl, setRepoUrl] = useState("");
  const [branch, setBranch] = useState("");
  const [manifestPath, setManifestPath] = useState("");
  const [manifestText, setManifestText] = useState("");
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [confirmed, setConfirmed] = useState<ConfirmedService | null>(null);
  const [loading, setLoading] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runtimeChoice, setRuntimeChoice] = useState<RuntimeChoice>("unsure");
  const [runtimeEvidence, setRuntimeEvidence] = useState<RuntimeEvidence>(initialEvidence);
  const [registrationAcknowledged, setRegistrationAcknowledged] = useState(false);
  const [examplePreviewOnly, setExamplePreviewOnly] = useState<WorkshopExample | null>(null);
  const [copyNotice, setCopyNotice] = useState<string | null>(null);
  const [managedServices, setManagedServices] = useState<ManagedRuntimeService[]>([]);

  const generatedManifest = useMemo(() => buildGuidedManifest(form), [form]);
  const generatedJson = useMemo(() => JSON.stringify(generatedManifest, null, 2), [generatedManifest]);
  const canConfirm = Boolean(
    preview?.service &&
      preview.status !== "invalid" &&
      registrationAcknowledged &&
      !examplePreviewOnly,
  );
  const activeStep = confirmed ? 5 : preview ? (registrationAcknowledged ? 4 : 3) : 1;

  async function loadManagedServices() {
    if (!user || !["node_manager", "platform_admin"].includes(user.role)) return;
    const response = await fetch("/api/services?include_archived=true", { cache: "no-store" });
    if (!response.ok) return;
    const data = await response.json();
    setManagedServices(Array.isArray(data) ? data : []);
  }

  useEffect(() => {
    void loadManagedServices();
  }, [user?.id]);

  function resetReviewState() {
    setPreview(null);
    setConfirmed(null);
    setError(null);
    setRegistrationAcknowledged(false);
    setRuntimeChoice("unsure");
    setRuntimeEvidence(initialEvidence);
  }

  function changeMode(nextMode: EntryMode) {
    setMode(nextMode);
    setExamplePreviewOnly(null);
    resetReviewState();
  }

  function updateForm<K extends keyof GuidedServiceForm>(key: K, value: GuidedServiceForm[K]) {
    setForm((current) => ({ ...current, [key]: value }));
    setExamplePreviewOnly(null);
    resetReviewState();
  }

  async function checkManualManifest(manifest: Record<string, unknown>, source: string, revision: string, path: string) {
    setLoading(true);
    resetReviewState();
    try {
      const response = await fetch(`${API_BASE_URL}/services/import/preview-manual`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          repo_url: source || "provider-supplied",
          branch: revision || "unversioned",
          manifest_path: path || "ai-effect.service.json",
          manifest,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(formatApiError(data?.detail) || "Service check failed.");
      setPreview(data);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Service check failed.");
    } finally {
      setLoading(false);
    }
  }

  async function checkGuidedDetails() {
    if (!form.serviceId.trim()) {
      setError("Enter a distinct service ID before checking this service.");
      setPreview(null);
      return;
    }
    await checkManualManifest(
      generatedManifest,
      form.sourceReference,
      form.sourceRevision,
      "guided/ai-effect.service.json",
    );
  }

  async function checkPastedManifest() {
    try {
      await checkManualManifest(
        JSON.parse(manifestText) as Record<string, unknown>,
        repoUrl,
        branch,
        manifestPath,
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Manifest JSON is invalid.");
    }
  }

  async function checkGitManifest() {
    setLoading(true);
    resetReviewState();
    try {
      const response = await fetch(`${API_BASE_URL}/services/import/preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_url: repoUrl, branch, manifest_path: manifestPath }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(formatApiError(data?.detail) || "Git manifest check failed.");
      setPreview(data);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Git manifest check failed.");
    } finally {
      setLoading(false);
    }
  }

  async function submitRequest() {
    if (!preview?.raw_manifest || !canConfirm) return;
    setConfirming(true);
    setConfirmed(null);
    setError(null);
    try {
      const source = mode === "guided" ? form.sourceReference : repoUrl;
      const revision = mode === "guided" ? form.sourceRevision : branch;
      const path = mode === "guided" ? "guided/ai-effect.service.json" : manifestPath;
      const response = await fetch(`${API_BASE_URL}/services/import/confirm-manual`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          repo_url: source || "provider-supplied",
          branch: revision || "unversioned",
          manifest_path: path || "ai-effect.service.json",
          manifest: preview.raw_manifest,
          onboarding: {
            source_type: mode === "git" ? "public_git" : "manual_manifest",
            source_revision: revision || null,
            runtime_status: runtimeChoice === "already_running" ? "already_running" : "needs_deployment",
            revision_pinned: runtimeEvidence.revisionPinned,
            image_reviewed: runtimeEvidence.imageReviewed,
            secrets_external: runtimeEvidence.secretsExternal,
            health_verified: runtimeEvidence.healthVerified,
            registration_only_acknowledged: registrationAcknowledged,
          },
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(formatApiError(data?.detail) || "Submission failed.");
      setConfirmed(data);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Submission failed.");
    } finally {
      setConfirming(false);
    }
  }

  function loadWorkshopExample(example: WorkshopExample) {
    setMode("manual");
    setRepoUrl(`${example.sourceUrl} @ ${example.revision} · ${example.manifestPath}`);
    setBranch(example.revision);
    setManifestPath("reference-example.json");
    setManifestText(JSON.stringify(example.manifest, null, 2));
    setExamplePreviewOnly(example);
    resetReviewState();
  }

  function useExampleAsStartingPoint() {
    if (!examplePreviewOnly) return;
    const example = examplePreviewOnly;
    setForm({
      ...formFromExample(example.manifest),
      sourceReference: `${example.sourceUrl} @ ${example.revision} · ${example.manifestPath}`,
      sourceRevision: example.revision,
    });
    setMode("guided");
    setExamplePreviewOnly(null);
    resetReviewState();
  }

  async function copyGeneratedJson() {
    await navigator.clipboard.writeText(generatedJson);
    setCopyNotice("Copied");
    window.setTimeout(() => setCopyNotice(null), 1600);
  }

  function downloadGeneratedJson() {
    const blob = new Blob([generatedJson], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${form.serviceId.trim() || "ai-effect-service"}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="page publish-page" style={{ maxWidth: 1380 }}>
      <header className="publish-hero">
        <p style={eyebrowStyle}>Service onboarding</p>
        <h1>Publish a service</h1>
        <p>
          Describe your service, add its technical connection details, and submit it for platform review.
        </p>
        <div className="registration-boundary">Registration records service metadata. It does not deploy, approve, or activate a service.</div>
        <Link href="/catalogue" style={secondaryButtonStyle}>View catalogue</Link>
        {user?.role === "platform_admin" && <Link href="/admin" style={secondaryButtonStyle}>Admin governance</Link>}
      </header>

      <section className="onboarding-boundary-grid" aria-label="Who does what">
        <Boundary title="Node owner" text="Supplies the service purpose, description, inputs, and outputs." />
        <Boundary title="Technical colleague" text="Supplies the container and execution-interface details." />
        <Boundary title="Platform team" text="Verifies runtime and integration evidence, then decides whether to approve the service." />
      </section>

      {managedServices.length > 0 && (
        <section style={{ ...cardStyle, marginTop: 20 }}>
          <p style={eyebrowStyle}>Runtime management</p>
          <h2 style={sectionTitleStyle}>Correct and verify onboarded services</h2>
          <p style={helpTextStyle}>Node providers can manage services assigned to their node; platform administrators can manage all services. Saving runtime or interface metadata invalidates earlier verification.</p>
          <div style={{ display: "grid", gap: 10 }}>
            {managedServices.map((service) => <ServiceRuntimeManager key={service.id} service={service} onUpdated={loadManagedServices} />)}
          </div>
        </section>
      )}

      <div className="publish-workbench">
        <aside className="card publish-step-card">
          <p style={{ ...eyebrowStyle, marginBottom: 16 }}>Progress</p>
          {[
            ["1", "Enter details", "Service, interface, and source"],
            ["2", "Check details", "Readable summary and validation"],
            ["3", "Runtime", "Provider claims and evidence"],
            ["4", "Submit", "Await administrator review"],
            ["5", "Admin decision", "Approve and activate"],
          ].map(([number, title, detail], index) => (
            <div className={`publish-step${index + 1 === activeStep ? " publish-step-active" : ""}`} key={number}>
              <span className="publish-step-number">{number}</span>
              <div><strong>{title}</strong><small>{detail}</small></div>
            </div>
          ))}
          <div className="publish-step-note">
            <strong>Count services, not use cases</strong>
            <span>Register each independently callable service separately. A solution can combine several services.</span>
          </div>
        </aside>

        <div className="publish-main-column">
          <section style={cardStyle}>
            <p style={eyebrowStyle}>1 · Enter service details</p>
            <h2 style={sectionTitleStyle}>How would you like to provide the details?</h2>
            <div style={tabRowStyle}>
              <ModeButton active={mode === "guided"} onClick={() => changeMode("guided")}>Guided form</ModeButton>
              <ModeButton active={mode === "git"} onClick={() => changeMode("git")}>Public Git manifest</ModeButton>
              <ModeButton active={mode === "manual"} onClick={() => changeMode("manual")}>Paste JSON</ModeButton>
            </div>

            {mode === "guided" && (
              <GuidedForm
                form={form}
                onChange={updateForm}
                generatedJson={generatedJson}
                onCopy={copyGeneratedJson}
                onDownload={downloadGeneratedJson}
                copyNotice={copyNotice}
                onCheck={checkGuidedDetails}
                loading={loading}
              />
            )}

            {mode === "git" && (
              <ImportFields
                repoUrl={repoUrl} branch={branch} manifestPath={manifestPath}
                onRepo={(value) => { setRepoUrl(value); resetReviewState(); }}
                onBranch={(value) => { setBranch(value); resetReviewState(); }}
                onPath={(value) => { setManifestPath(value); resetReviewState(); }}
                git
              >
                <button style={primaryButtonStyle} type="button" onClick={checkGitManifest} disabled={loading}>
                  {loading ? "Checking…" : "Check service details"}
                </button>
              </ImportFields>
            )}

            {mode === "manual" && (
              <ImportFields
                repoUrl={repoUrl} branch={branch} manifestPath={manifestPath}
                onRepo={(value) => { setRepoUrl(value); resetReviewState(); }}
                onBranch={(value) => { setBranch(value); resetReviewState(); }}
                onPath={(value) => { setManifestPath(value); resetReviewState(); }}
              >
                <label style={labelStyle}>Manifest JSON
                  <textarea
                    value={manifestText}
                    onChange={(event) => { setManifestText(event.target.value); resetReviewState(); }}
                    spellCheck={false}
                    style={textareaStyle}
                  />
                </label>
                <p style={helpTextStyle}>The original JSON is submitted unchanged, including fields the guided form does not know about.</p>
                <button style={primaryButtonStyle} type="button" onClick={checkPastedManifest} disabled={loading}>
                  {loading ? "Checking…" : "Check service details"}
                </button>
              </ImportFields>
            )}

            <details className="publish-help-details">
              <summary>Examples, supported sources, and current limitations</summary>
              <p>Public Git reads one exact JSON file. Paste JSON preserves the complete object. Private repositories, ZIP upload, automatic Dockerfile discovery, Compose execution, and container deployment are not performed here.</p>
              <details className="workshop-example-panel">
                <summary>View reference examples</summary>
                <p>These four node examples are preview-only. They cannot be submitted until you explicitly use one as a starting point and give the new service a distinct name and ID.</p>
                <div className="workshop-example-buttons">
                  {workshopExamples.map((example) => (
                    <button type="button" key={example.key} onClick={() => loadWorkshopExample(example)}>
                      <strong>{example.country}</strong><span>{example.service}</span>
                    </button>
                  ))}
                </div>
              </details>
            </details>
            {error && <div style={errorBoxStyle}>{error}</div>}
          </section>

          {preview && (
            <section style={cardStyle}>
              <div style={rowBetweenStyle}>
                <div><p style={eyebrowStyle}>2 · Check service details</p><h2 style={sectionTitleStyle}>Review before submitting</h2></div>
                <span style={statusBadgeStyle(preview.status)}>{preview.status.toUpperCase()}</span>
              </div>

              {preview.service && <ServicePreview service={preview.service} />}
              <ValidationSummary validation={preview.validation} />

              {examplePreviewOnly && (
                <div className="example-preview-lock">
                  <strong>Preview only</strong>
                  <p>This pinned example cannot be submitted as another production service. Create a distinct record and review the provider details first.</p>
                  <button type="button" style={smallButtonStyle} onClick={useExampleAsStartingPoint}>Use as starting point</button>
                </div>
              )}

              {preview.service && !examplePreviewOnly && (
                <RuntimeSection
                  choice={runtimeChoice}
                  onChoice={(value) => { setRuntimeChoice(value); setRegistrationAcknowledged(false); }}
                  evidence={runtimeEvidence}
                  onEvidence={(field, checked) => setRuntimeEvidence((current) => ({ ...current, [field]: checked }))}
                  service={preview.service}
                  acknowledged={registrationAcknowledged}
                  onAcknowledge={setRegistrationAcknowledged}
                />
              )}

              {!examplePreviewOnly && preview.service && (
                <button
                  type="button" onClick={submitRequest} disabled={!canConfirm || confirming}
                  style={{ ...primaryButtonStyle, opacity: !canConfirm || confirming ? 0.55 : 1 }}
                >
                  {confirming ? "Submitting…" : "Submit for administrator review"}
                </button>
              )}
            </section>
          )}

          {confirmed && (
            <section style={successCardStyle}>
              <p style={eyebrowStyle}>Submitted</p>
              <h2 style={sectionTitleStyle}>Submitted — awaiting administrator review</h2>
              <p>{confirmed.name} is registered as <strong>{confirmed.trust_badge}</strong>. Submission did not deploy or activate its container.</p>
              <div className="onboarding-next-steps">
                <strong>Next steps</strong>
                <ol>
                  <li>The provider or platform operator supplies any missing runtime evidence.</li>
                  <li>An administrator verifies ownership, source, image, secrets, health, and contract.</li>
                  <li>Only an administrator can approve and activate the service.</li>
                </ol>
              </div>
              <Link href="/catalogue" style={secondaryButtonStyle}>Open catalogue</Link>
              {user?.role === "platform_admin" && <Link href="/admin" style={primaryLinkStyle}>Review in Admin</Link>}
            </section>
          )}
        </div>
      </div>
    </main>
  );
}

function Boundary({ title, text }: { title: string; text: string }) {
  return <div className="onboarding-boundary-card"><span>{title}</span><p>{text}</p></div>;
}

function ModeButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return <button type="button" onClick={onClick} style={active ? activeTabStyle : tabStyle}>{children}</button>;
}

function GuidedForm({
  form, onChange, generatedJson, onCopy, onDownload, copyNotice, onCheck, loading,
}: {
  form: GuidedServiceForm;
  onChange: <K extends keyof GuidedServiceForm>(key: K, value: GuidedServiceForm[K]) => void;
  generatedJson: string;
  onCopy: () => void;
  onDownload: () => void;
  copyNotice: string | null;
  onCheck: () => void;
  loading: boolean;
}) {
  return (
    <div className="guided-form">
      <div className="guided-section">
        <h3>Service description</h3>
        <div className="guided-grid">
          <Field label="Service name" value={form.name} onChange={(v) => onChange("name", v)} required />
          <Field label="Provider display name" value={form.provider} onChange={(v) => onChange("provider", v)} required help="Descriptive only. Your signed-in account and assigned node control ownership and permissions." />
          <Field label="Category" value={form.category} onChange={(v) => onChange("category", v)} required />
          <Field label="Version" value={form.version} onChange={(v) => onChange("version", v)} required />
          <Field label="Input data / DataReference type" value={form.inputType} onChange={(v) => onChange("inputType", v)} required />
          <Field label="Output data / DataReference type" value={form.outputType} onChange={(v) => onChange("outputType", v)} required />
          <label style={{ ...labelStyle, gridColumn: "1 / -1" }}>Description
            <textarea value={form.description} onChange={(e) => onChange("description", e.target.value)} style={{ ...textareaStyle, minHeight: 100 }} />
          </label>
        </div>
      </div>

      <div className="guided-section">
        <h3>Technical details</h3>
        <div className="guided-grid">
          <Field label="Unique service ID" value={form.serviceId} onChange={(v) => onChange("serviceId", v)} required help="Use a stable, lowercase identifier. It cannot duplicate an existing catalogue service." />
          <Field label="Container name" value={form.containerName} onChange={(v) => onChange("containerName", v)} required />
          <Field
            label="Runtime network host"
            value={form.internalHost}
            onChange={(v) => onChange("internalHost", v)}
            required
            help="The hostname reachable from the platform network. It may differ from the logical service name."
          />
          <Field label="Docker image" value={form.image} onChange={(v) => onChange("image", v)} help="Provide an image or a Dockerfile path. A pre-built, pinned image is preferred." />
          <Field label="Dockerfile path" value={form.dockerfile} onChange={(v) => onChange("dockerfile", v)} />
          <Field label="Internal port" value={form.internalPort} onChange={(v) => onChange("internalPort", v)} required />
          <Field label="Health path" value={form.healthPath} onChange={(v) => onChange("healthPath", v)} required />
          <Field label="Operation name" value={form.operationName} onChange={(v) => onChange("operationName", v)} required />
          <label style={labelStyle}>Interface type
            <select value={form.interfaceType} onChange={(e) => onChange("interfaceType", e.target.value as InterfaceChoice)} style={inputStyle}>
              <option value="control">AI-EFFECT Control</option>
              <option value="http">REST / HTTP</option>
              <option value="grpc">gRPC</option>
              <option value="container_job">Script / batch container</option>
              <option value="legacy_sidecar">Legacy adapter</option>
            </select>
            <small style={fieldHelpStyle}>{interfaceHelp(form.interfaceType)}</small>
          </label>
          <Field label={form.interfaceType === "grpc" ? "Proto contract path or URL" : "Contract reference"} value={form.contractUri} onChange={(v) => onChange("contractUri", v)} required={form.interfaceType === "grpc"} help="A declaration for review—not proof that the endpoint is reachable or compatible." />
          <details style={{ gridColumn: "1 / -1" }} className="technical-details">
            <summary>Advanced WP3 operation fields</summary>
            <div className="guided-grid" style={{ marginTop: 12 }}>
              <Field label="Input message name" value={form.inputMessageName} onChange={(v) => onChange("inputMessageName", v)} help="For example ProvideDataRequest. Supplied values are preserved exactly." />
              <Field label="Output message name" value={form.outputMessageName} onChange={(v) => onChange("outputMessageName", v)} help="For example ProvideDataResponse. Supplied values are preserved exactly." />
              <Field label="WP3 proto reference" value={form.protoUri} onChange={(v) => onChange("protoUri", v)} help="Separate compiler-facing proto_uri; it may differ from the review contract reference." />
            </div>
          </details>
          {form.interfaceType === "grpc" && <>
            <Field label="gRPC input message" value={form.grpcInputMessage} onChange={(v) => onChange("grpcInputMessage", v)} />
            <Field label="gRPC output message" value={form.grpcOutputMessage} onChange={(v) => onChange("grpcOutputMessage", v)} />
          </>}
          {form.interfaceType === "http" && <>
            <Field label="HTTP method" value={form.httpMethod} onChange={(v) => onChange("httpMethod", v)} required />
            <Field label="HTTP operation path" value={form.httpPath} onChange={(v) => onChange("httpPath", v)} required />
          </>}
          {form.interfaceType === "container_job" && <Field label="Container command" value={form.jobCommand} onChange={(v) => onChange("jobCommand", v)} required />}
          {form.interfaceType === "legacy_sidecar" && <Field label="Adapter type" value={form.legacyAdapter} onChange={(v) => onChange("legacyAdapter", v)} help="Recommended so operators know which adapter must be deployed." />}
          <Field label="Source reference" value={form.sourceReference} onChange={(v) => onChange("sourceReference", v)} required help="Repository URL, package location, or another traceable provider reference." />
          <Field label="Source revision" value={form.sourceRevision} onChange={(v) => onChange("sourceRevision", v)} help="Prefer an immutable commit SHA or release tag." />
        </div>
      </div>

      <details className="generated-json">
        <summary>View generated manifest JSON</summary>
        <div><button type="button" onClick={onCopy} style={smallButtonStyle}>{copyNotice || "Copy JSON"}</button><button type="button" onClick={onDownload} style={smallButtonStyle}>Download JSON</button></div>
        <pre>{generatedJson}</pre>
      </details>
      <button type="button" onClick={onCheck} disabled={loading} style={primaryButtonStyle}>{loading ? "Checking…" : "Check service details"}</button>
    </div>
  );
}

function Field({ label, value, onChange, required, help }: { label: string; value: string; onChange: (value: string) => void; required?: boolean; help?: string }) {
  return <label style={labelStyle}>{label}{required && <span className="required-label">Required</span>}<input value={value} onChange={(e) => onChange(e.target.value)} style={inputStyle} />{help && <small style={fieldHelpStyle}>{help}</small>}</label>;
}

function ImportFields({ repoUrl, branch, manifestPath, onRepo, onBranch, onPath, git, children }: {
  repoUrl: string; branch: string; manifestPath: string; onRepo: (v: string) => void; onBranch: (v: string) => void; onPath: (v: string) => void; git?: boolean; children: React.ReactNode;
}) {
  return <div className="guided-form">
    <div className="guided-grid">
      <Field label={git ? "Public repository URL" : "Source reference"} value={repoUrl} onChange={onRepo} required />
      <Field label="Commit SHA, tag, or revision" value={branch} onChange={onBranch} required={git} />
      <div style={{ gridColumn: "1 / -1" }}><Field label={git ? "Exact JSON manifest path" : "Manifest name or path"} value={manifestPath} onChange={onPath} required={git} /></div>
    </div>
    {git && <p style={helpTextStyle}>Git import fetches only the exact JSON path. Use a commit SHA or immutable tag when possible.</p>}
    {children}
  </div>;
}

function ServicePreview({ service }: { service: ImportedService }) {
  return <div style={previewBoxStyle}>
    <h3 style={previewTitleStyle}>{service.name}</h3>
    <p style={previewDescriptionStyle}>{service.description || "No description provided."}</p>
    <div style={detailsGridStyle}>
      <Detail label="Provider" value={service.provider} />
      <Detail label="Operation" value={service.operation_name} />
      <Detail label="Input" value={service.input_type || "Not declared"} />
      <Detail label="Output" value={service.output_type || "Not declared"} />
      <Detail label="Next action" value="Review runtime claims and submit for admin review" />
    </div>
    <details className="technical-details"><summary>Technical details</summary>
      <div style={detailsGridStyle}>
        <Detail label="Service ID" value={service.id || "Generated on submission"} />
        <Detail label="Category / version" value={`${service.category} · ${service.version}`} />
        <Detail label="Interface" value={service.interface_type} />
        <Detail label="Orchestration" value={service.orchestration_mode} />
        <Detail label="Adapter" value={service.adapter_type || "Not declared"} />
        <Detail label="Image / Dockerfile" value={service.image || service.dockerfile || "Missing"} />
        <Detail label="Logical container" value={service.container_name} />
        <Detail label="Runtime network host" value={service.internal_host} />
        <Detail label="Configured health URL" value={`http://${service.internal_host}:${service.internal_port}${service.health_path}`} />
        <Detail label="Contract reference" value={service.contract_uri || service.proto_uri || "Not declared"} />
        <Detail label="Compatibility proto_uri" value={service.proto_uri || "Not declared"} />
        <Detail label="Input message" value={service.input_message_name || "Not declared"} />
        <Detail label="Output message" value={service.output_message_name || "Not declared"} />
        <Detail label="Recorded source" value={`${service.repository_url} @ ${service.repository_branch}`} />
      </div>
    </details>
  </div>;
}

function ValidationSummary({ validation }: { validation: ValidationMessage[] }) {
  const errors = validation.filter((item) => item.level === "error");
  const actionableWarnings = validation.filter((item) => item.level === "warning" && !isCompilerInfo(item.message));
  const compilerInfo = validation.filter((item) => item.level === "warning" && isCompilerInfo(item.message));
  const successes = validation.filter((item) => item.level === "success");
  return <div className="validation-summary">
    {errors.map((item, i) => <ValidationItem key={`e-${i}`} level="error" title="Fix required" message={item.message} />)}
    {actionableWarnings.map((item, i) => <ValidationItem key={`w-${i}`} level="warning" title="Review recommended" message={item.message} />)}
    {compilerInfo.length > 0 && <details><summary>Compiler compatibility information</summary>{compilerInfo.map((item, i) => <p key={i}>{item.message}</p>)}</details>}
    <details><summary>All validation details ({validation.length})</summary>{successes.map((item, i) => <p key={i}>✓ {item.message}</p>)}</details>
  </div>;
}

function ValidationItem({ level, title, message }: { level: ValidationMessage["level"]; title: string; message: string }) {
  return <div style={validationItemStyle(level)}><strong>{title}</strong><span>{message}</span></div>;
}

function RuntimeSection({ choice, onChoice, evidence, onEvidence, service, acknowledged, onAcknowledge }: {
  choice: RuntimeChoice; onChoice: (value: RuntimeChoice) => void; evidence: RuntimeEvidence; onEvidence: (field: keyof RuntimeEvidence, checked: boolean) => void; service: ImportedService; acknowledged: boolean; onAcknowledge: (value: boolean) => void;
}) {
  return <div className="onboarding-runtime-panel">
    <div><p style={eyebrowStyle}>3 · Runtime readiness</p><h3>What happens after registration?</h3><p>These are provider claims for administrator review. None are automatically checked.</p></div>
    <div className="onboarding-runtime-choice">
      {([
        ["needs_deployment", "Needs deployment", "An operator must build or pull and start it."],
        ["already_running", "Provider reports running", "An administrator must still verify it from production."],
        ["unsure", "Not sure", "Recorded conservatively as needing deployment until verified."],
      ] as Array<[RuntimeChoice, string, string]>).map(([value, title, text]) => <label key={value}><input type="radio" name="runtime" checked={choice === value} onChange={() => onChoice(value)} /><span><strong>{title}</strong><small>{text}</small></span></label>)}
    </div>
    <div className="onboarding-evidence-grid">
      {([
        ["revisionPinned", "Exact source revision recorded"],
        ["imageReviewed", "Docker image built or reviewed"],
        ["secretsExternal", "Secrets kept outside source and manifest"],
        ["healthVerified", `Provider reports testing ${service.internal_host}:${service.internal_port}${service.health_path}`],
      ] as Array<[keyof RuntimeEvidence, string]>).map(([field, label]) => <label key={field}><input type="checkbox" checked={evidence[field]} onChange={(e) => onEvidence(field, e.target.checked)} /><span>{label}</span></label>)}
    </div>
    <label className="onboarding-acknowledgement"><input type="checkbox" checked={acknowledged} onChange={(e) => onAcknowledge(e.target.checked)} /><span>I understand this submits metadata for review and does not deploy or activate the service.</span></label>
  </div>;
}

function Detail({ label, value }: { label: string; value: string }) {
  return <div style={detailStyle}><span style={detailLabelStyle}>{label}</span><span style={detailValueStyle}>{value}</span></div>;
}

function isCompilerInfo(message: string) {
  return message.includes("Short-term compiler compatibility") || message.includes("will use AI-EFFECT Control Interface");
}

function interfaceHelp(type: InterfaceChoice) {
  if (type === "grpc") return "gRPC requires a .proto reference and operation information. Message names should be supplied when the contract defines them.";
  if (type === "http") return "REST services require an HTTP method and path and may need a deployed Control Interface adapter. Selecting REST does not create that adapter.";
  if (type === "container_job") return "Batch services require a container command and may need a deployed Control Interface adapter. Selecting batch does not create that adapter.";
  if (type === "legacy_sidecar") return "Declare the existing adapter type. This page records it but does not generate or deploy an adapter.";
  return "Use this only when the service already implements the AI-EFFECT Control Interface; this page does not add the interface to a container.";
}

function formatApiError(detail: unknown): string | null {
  if (!detail) return null;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((item) => typeof item === "string" ? item : JSON.stringify(item)).join(" ");
  return JSON.stringify(detail);
}

function statusBadgeStyle(status: PreviewResponse["status"]): CSSProperties {
  return { ...badgeStyle, ...(status === "valid" ? { background: "#ecfdf5", color: "#047857", borderColor: "#a7f3d0" } : status === "warning" ? { background: "#fffbeb", color: "#92400e", borderColor: "#fde68a" } : { background: "#fef2f2", color: "#b91c1c", borderColor: "#fecaca" }) };
}

function validationItemStyle(level: ValidationMessage["level"]): CSSProperties {
  const colors = level === "error" ? { borderColor: "#fecaca", background: "#fef2f2" } : { borderColor: "#fde68a", background: "#fffbeb" };
  return { display: "grid", gap: 4, padding: 13, border: "1px solid", borderRadius: 12, ...colors };
}

const eyebrowStyle: CSSProperties = { margin: 0, fontSize: 12, fontWeight: 800, letterSpacing: ".08em", textTransform: "uppercase", color: "#6543df" };
const cardStyle: CSSProperties = { background: "#fff", border: "1px solid #e5e4f1", borderRadius: 18, padding: 22, boxShadow: "0 12px 32px rgba(30,24,70,.07)", marginBottom: 22 };
const successCardStyle: CSSProperties = { ...cardStyle, borderColor: "#bbf7d0", background: "#f0fdf4" };
const sectionTitleStyle: CSSProperties = { margin: "6px 0 16px", fontSize: 24, color: "#0f172a" };
const tabRowStyle: CSSProperties = { display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 18 };
const tabStyle: CSSProperties = { border: "1px solid #cbd5e1", background: "#f8fafc", color: "#334155", borderRadius: 999, padding: "9px 14px", fontWeight: 750, cursor: "pointer" };
const activeTabStyle: CSSProperties = { ...tabStyle, background: "#f0ecff", color: "#4f2bc9", borderColor: "#c9bcfa" };
const labelStyle: CSSProperties = { display: "flex", flexDirection: "column", gap: 7, fontSize: 13, fontWeight: 750, color: "#334155" };
const inputStyle: CSSProperties = { width: "100%", border: "1px solid #cbd5e1", borderRadius: 11, padding: "10px 11px", fontSize: 14, background: "#fff" };
const textareaStyle: CSSProperties = { ...inputStyle, minHeight: 280, fontFamily: "ui-monospace, monospace", resize: "vertical" };
const fieldHelpStyle: CSSProperties = { color: "#73778d", fontWeight: 500, lineHeight: 1.4 };
const helpTextStyle: CSSProperties = { margin: "8px 0", color: "#64748b", fontSize: 13, lineHeight: 1.5 };
const primaryButtonStyle: CSSProperties = { marginTop: 14, border: 0, borderRadius: 11, padding: "11px 16px", color: "#fff", background: "linear-gradient(135deg,#5b2cf2,#4320ca)", fontWeight: 800, cursor: "pointer" };
const smallButtonStyle: CSSProperties = { border: "1px solid #cbd5e1", borderRadius: 9, padding: "7px 10px", background: "#fff", color: "#334155", fontWeight: 750, cursor: "pointer" };
const secondaryButtonStyle: CSSProperties = { display: "inline-flex", margin: "8px 8px 0 0", alignItems: "center", border: "1px solid #cbd5e1", borderRadius: 11, padding: "9px 13px", background: "#fff", color: "#334155", textDecoration: "none", fontWeight: 800 };
const primaryLinkStyle: CSSProperties = { ...secondaryButtonStyle, background: "#5b2cf2", borderColor: "#5b2cf2", color: "#fff" };
const errorBoxStyle: CSSProperties = { marginTop: 16, padding: 14, border: "1px solid #fecaca", borderRadius: 13, background: "#fef2f2", color: "#991b1b", fontWeight: 700 };
const rowBetweenStyle: CSSProperties = { display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 };
const badgeStyle: CSSProperties = { border: "1px solid", borderRadius: 999, padding: "7px 11px", fontSize: 12, fontWeight: 900 };
const previewBoxStyle: CSSProperties = { marginTop: 18, padding: 18, border: "1px solid #ddd8f4", borderRadius: 14, background: "#faf9ff" };
const previewTitleStyle: CSSProperties = { margin: 0, color: "#171a38", fontSize: 22 };
const previewDescriptionStyle: CSSProperties = { color: "#666b82", lineHeight: 1.5 };
const detailsGridStyle: CSSProperties = { display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(190px,1fr))", gap: 10 };
const detailStyle: CSSProperties = { display: "grid", gap: 3, padding: 10, borderRadius: 9, background: "#fff", overflowWrap: "anywhere" };
const detailLabelStyle: CSSProperties = { color: "#777d92", fontSize: 11, fontWeight: 800, textTransform: "uppercase" };
const detailValueStyle: CSSProperties = { color: "#252842", fontSize: 13, fontWeight: 700 };
