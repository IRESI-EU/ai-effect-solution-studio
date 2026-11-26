"use client";

import { Check, CircleAlert, CircleCheck, MapPin, Pencil, TriangleAlert } from "lucide-react";
import { useMemo, useState } from "react";
import { ServiceIcon } from "../../components/builder/service-icon";
import {
  WORKFLOW_OUTPUT,
  WORKFLOW_START,
  serviceIcon,
  servicePorts,
  serviceStage,
  serviceText,
} from "../../lib/service-presentation";
import type { GuidedServiceForm, InterfaceChoice, ProtoOperation } from "./guided-manifest";

export type CatalogueEntry = {
  id: string;
  name: string;
  provider: string;
  category: string;
  version: string;
  description?: string | null;
  status?: string;
  lifecycle_status?: string | null;
  input_type: string;
  output_type: string;
  operation_name?: string;
  owner_node?: string | null;
  interface_contract?: Record<string, unknown> | null;
};
export type PreviewResponse = {
  status: "valid" | "warning" | "invalid";
  raw_manifest: Record<string, unknown>;
  service: Record<string, unknown> | null;
  validation: { level: "success" | "warning" | "error"; message: string }[];
};
export type RuntimeChoice = "needs_deployment" | "already_running" | "unsure";
export type Evidence = { revisionPinned: boolean; imageReviewed: boolean; secretsExternal: boolean; healthVerified: boolean };
type Update = <K extends keyof GuidedServiceForm>(key: K, value: GuidedServiceForm[K]) => void;

const CATEGORY_SUGGESTIONS = ["Data source", "Data preparation", "Simulation", "Forecasting", "Optimisation", "Analysis", "Reporting", "Visualisation"];

export function TextField({ label, value, onChange, placeholder, hint, wide, required }: {
  label: string; value: string; onChange: (value: string) => void; placeholder?: string; hint?: string; wide?: boolean; required?: boolean;
}) {
  return (
    <label className={`wizard-field${wide ? " wizard-field--wide" : ""}`}>
      <span className="wizard-field__label">{label}{required && <em aria-hidden="true"> *</em>}</span>
      <input className="ae-input" value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} />
      {hint && <small>{hint}</small>}
    </label>
  );
}

function usable(catalogue: CatalogueEntry[]) {
  return catalogue.filter((entry) => (entry.status || "approved") === "approved" && !["archived", "deprecated"].includes(entry.lifecycle_status || "active"));
}

/* ------------------------------------------------------------------ Describe */

export function DescribeStep({ form, update, catalogue, nodeLabel, isExample }: {
  form: GuidedServiceForm; update: Update; catalogue: CatalogueEntry[]; nodeLabel: string | null; isExample: boolean;
}) {
  const [editId, setEditId] = useState(false);
  const live = useMemo(() => usable(catalogue), [catalogue]);

  // Data other services produce (to follow them) and data they take (to feed them).
  const producedBy = useMemo(() => {
    const map = new Map<string, string>();
    live.forEach((entry) => {
      if (entry.output_type && entry.output_type !== WORKFLOW_OUTPUT && !map.has(entry.output_type)) map.set(entry.output_type, serviceText(entry).title);
    });
    return map;
  }, [live]);
  const takenBy = useMemo(() => {
    const map = new Map<string, string>();
    live.forEach((entry) => {
      if (entry.input_type && entry.input_type !== WORKFLOW_START && !map.has(entry.input_type)) map.set(entry.input_type, serviceText(entry).title);
    });
    return map;
  }, [live]);

  const inputMode = form.inputType === WORKFLOW_START ? "start" : producedBy.has(form.inputType) ? "follow" : form.inputType ? "own" : "";
  const outputMode = form.outputType === WORKFLOW_OUTPUT ? "end" : takenBy.has(form.outputType) ? "feed" : form.outputType ? "own" : "";
  const base = form.name.trim() || "My service";

  return (
    <>
      <h2 className="wizard-card__title">Describe your service</h2>
      <p className="wizard-card__lead">Write for a researcher from another node: they will find your service by this description, and Design with AI uses it to pick services.</p>

      <div className="wizard-grid">
        <TextField label="Service name" required value={form.name} onChange={(value) => update("name", value)} placeholder="e.g. Household load forecaster" wide />
        <label className="wizard-field wizard-field--wide">
          <span className="wizard-field__label">What does it do?<em aria-hidden="true"> *</em></span>
          <textarea className="ae-input" rows={4} value={form.description} onChange={(event) => update("description", event.target.value)}
            placeholder="e.g. Forecasts household electricity use for the next 24 hours from half-hourly smart-meter readings." />
          <small>One to three sentences: what goes in, what comes out, and why it is useful.</small>
        </label>
        <TextField label="Provider" required value={form.provider} onChange={(value) => update("provider", value)} hint={nodeLabel ? `Your node: ${nodeLabel}.` : "Your organisation or node."} />
        <TextField label="Version" value={form.version} onChange={(value) => update("version", value)} hint="For example 1.0.0." />
        <label className="wizard-field">
          <span className="wizard-field__label">Category</span>
          <input className="ae-input" list="category-suggestions" value={form.category} onChange={(event) => update("category", event.target.value)} placeholder="e.g. Forecasting" />
          <datalist id="category-suggestions">{CATEGORY_SUGGESTIONS.map((c) => <option key={c} value={c} />)}</datalist>
        </label>
      </div>

      <h3 className="wizard-section">Where does it fit in a workflow?</h3>
      <p className="wizard-card__lead">This decides which services it can be connected to in the Builder.</p>
      <div className="fit-grid">
        <fieldset className="fit-choice">
          <legend>What does it take?</legend>
          <Radio name="input" checked={inputMode === "start"} onChange={() => update("inputType", WORKFLOW_START)} title="Nothing: it starts a workflow" text="It loads or creates its own data." />
          <Radio name="input" checked={inputMode === "follow"} onChange={() => update("inputType", producedBy.keys().next().value || "")} title="The result of another service" text="Choose the service whose result it uses." disabled={producedBy.size === 0} />
          {inputMode === "follow" && (
            <select className="ae-input" value={form.inputType} onChange={(event) => update("inputType", event.target.value)} aria-label="Service whose result it uses">
              {[...producedBy.entries()].map(([type, title]) => <option key={type} value={type}>{title}</option>)}
            </select>
          )}
          <Radio name="input" checked={inputMode === "own"} onChange={() => update("inputType", `${base} input`)} title="Its own kind of data" text="Name the data it expects." />
          {inputMode === "own" && <input className="ae-input" value={form.inputType} onChange={(event) => update("inputType", event.target.value)} aria-label="Name of the data it takes" />}
        </fieldset>
        <fieldset className="fit-choice">
          <legend>What does it produce?</legend>
          <Radio name="output" checked={outputMode === "end"} onChange={() => update("outputType", WORKFLOW_OUTPUT)} title="A final result" text="It ends a workflow: results, a report, drawings." />
          <Radio name="output" checked={outputMode === "feed"} onChange={() => update("outputType", takenBy.keys().next().value || "")} title="Data another service takes" text="Choose the service that uses its result." disabled={takenBy.size === 0} />
          {outputMode === "feed" && (
            <select className="ae-input" value={form.outputType} onChange={(event) => update("outputType", event.target.value)} aria-label="Service that uses its result">
              {[...takenBy.entries()].map(([type, title]) => <option key={type} value={type}>{title}</option>)}
            </select>
          )}
          <Radio name="output" checked={outputMode === "own"} onChange={() => update("outputType", `${base} output`)} title="Its own kind of data" text="Name the data, so a later service can take it." />
          {outputMode === "own" && <input className="ae-input" value={form.outputType} onChange={(event) => update("outputType", event.target.value)} aria-label="Name of the data it produces" />}
        </fieldset>
      </div>

      <div className="wizard-id">
        <span>Catalogue ID: <code>{form.serviceId || "set automatically from the name"}</code></span>
        <button type="button" className="link-button" onClick={() => setEditId((open) => !open)}><Pencil size={13} aria-hidden="true" /> {editId ? "Done" : "Change"}</button>
        {editId && <input className="ae-input" value={form.serviceId} onChange={(event) => update("serviceId", event.target.value.toLowerCase())} aria-label="Catalogue ID" />}
      </div>
    </>
  );
}

function Radio({ name, checked, onChange, title, text, disabled }: { name: string; checked: boolean; onChange: () => void; title: string; text: string; disabled?: boolean }) {
  return (
    <label className={`fit-option${checked ? " is-checked" : ""}${disabled ? " is-disabled" : ""}`}>
      <input type="radio" name={name} checked={checked} onChange={onChange} disabled={disabled} />
      <span><strong>{title}</strong><small>{text}</small></span>
    </label>
  );
}

/* ------------------------------------------------------------------ Connect */

const INTERFACES: { key: InterfaceChoice; title: string; text: string; badge?: string }[] = [
  { key: "control", title: "AI-EFFECT control interface", text: "The service answers POST /control/execute, /status and /output.", badge: "Recommended" },
  { key: "grpc", title: "gRPC", text: "The service has a .proto contract and a gRPC server." },
  { key: "http", title: "REST / HTTP API", text: "An existing web API; a small adapter connects it." },
  { key: "container_job", title: "Script or batch job", text: "A container that runs a command and exits; an adapter runs it." },
  { key: "legacy_sidecar", title: "Older service with an adapter", text: "An existing service wrapped by a node's adapter." },
];

export function ConnectStep({ form, update, protoOperations, runtime, onRuntime }: {
  form: GuidedServiceForm; update: Update; protoOperations: ProtoOperation[]; runtime: RuntimeChoice; onRuntime: (value: RuntimeChoice) => void;
}) {
  function pickOperation(name: string) {
    const operation = protoOperations.find((candidate) => candidate.name === name);
    update("operationName", name);
    if (operation) {
      update("inputMessageName", operation.input);
      update("outputMessageName", operation.output);
      update("grpcInputMessage", operation.input);
      update("grpcOutputMessage", operation.output);
    }
  }

  return (
    <>
      <h2 className="wizard-card__title">How does the platform call it?</h2>
      <p className="wizard-card__lead">Usually a technical colleague fills this in. Values from a package, manifest or .proto are already here.</p>
      <div className="interface-grid" role="radiogroup" aria-label="Interface">
        {INTERFACES.map((option) => (
          <button key={option.key} type="button" role="radio" aria-checked={form.interfaceType === option.key}
            className={`interface-card${form.interfaceType === option.key ? " is-active" : ""}`} onClick={() => update("interfaceType", option.key)}>
            <strong>{option.title}{option.badge && <em>{option.badge}</em>}</strong>
            <span>{option.text}</span>
          </button>
        ))}
      </div>

      <div className="wizard-grid">
        <TextField label="Docker image" required value={form.image} onChange={(value) => update("image", value)} placeholder="registry.example.org/node/service:1.0.0" hint="Use a fixed version tag, not :latest." wide />
        <TextField label="Container name" required value={form.containerName} onChange={(value) => update("containerName", value)} placeholder="e.g. load-forecaster" hint="The name the container runs under on the AI-EFFECT services network." />
        <TextField label="Port" value={form.internalPort} onChange={(value) => update("internalPort", value)} hint="The port inside the container (often 8080)." />
        {protoOperations.length > 0 ? (
          <label className="wizard-field">
            <span className="wizard-field__label">Operation<em aria-hidden="true"> *</em></span>
            <select className="ae-input" value={form.operationName} onChange={(event) => pickOperation(event.target.value)}>
              {protoOperations.map((operation) => <option key={operation.name} value={operation.name}>{operation.name} ({operation.input} → {operation.output})</option>)}
            </select>
            <small>Read from your .proto file. Add each operation as its own service.</small>
          </label>
        ) : (
          <TextField label="Operation" required value={form.operationName} onChange={(value) => update("operationName", value)} placeholder="e.g. Forecast" hint="The method name the platform asks the service to run." />
        )}

        {form.interfaceType === "grpc" && (
          <>
            <TextField label=".proto file" value={form.protoUri} onChange={(value) => update("protoUri", value)} placeholder="microservice/model.proto" />
            <TextField label="Request message" value={form.grpcInputMessage} onChange={(value) => update("grpcInputMessage", value)} />
            <TextField label="Response message" value={form.grpcOutputMessage} onChange={(value) => update("grpcOutputMessage", value)} />
          </>
        )}
        {form.interfaceType === "http" && (
          <>
            <TextField label="HTTP method" value={form.httpMethod} onChange={(value) => update("httpMethod", value)} />
            <TextField label="Endpoint path" value={form.httpPath} onChange={(value) => update("httpPath", value)} placeholder="/predict" />
          </>
        )}
        {form.interfaceType === "container_job" && <TextField label="Command" value={form.jobCommand} onChange={(value) => update("jobCommand", value)} placeholder="python run.py" wide />}
        {form.interfaceType === "legacy_sidecar" && <TextField label="Adapter" value={form.legacyAdapter} onChange={(value) => update("legacyAdapter", value)} placeholder="e.g. portugal-sidecar" hint="Which adapter must run next to it." />}
      </div>

      <fieldset className="fit-choice fit-choice--row">
        <legend>Is it already running on the AI-EFFECT server?</legend>
        <Radio name="runtime" checked={runtime === "already_running"} onChange={() => onRuntime("already_running")} title="Yes" text="It is up on the services network." />
        <Radio name="runtime" checked={runtime === "needs_deployment"} onChange={() => onRuntime("needs_deployment")} title="Not yet" text="It still needs to be started there." />
        <Radio name="runtime" checked={runtime === "unsure"} onChange={() => onRuntime("unsure")} title="Not sure" text="The platform team will check." />
      </fieldset>

      <details className="wizard-advanced">
        <summary>Advanced settings</summary>
        <div className="wizard-grid">
          <TextField label="Network host" value={form.internalHost} onChange={(value) => update("internalHost", value)} hint="Only if it differs from the container name." />
          <TextField label="Health check path" value={form.healthPath} onChange={(value) => update("healthPath", value)} />
          <TextField label="Dockerfile path" value={form.dockerfile} onChange={(value) => update("dockerfile", value)} hint="Instead of an image, if the platform builds it." />
          {form.interfaceType !== "grpc" && (
            <>
              <TextField label="Input message name" value={form.inputMessageName} onChange={(value) => update("inputMessageName", value)} />
              <TextField label="Output message name" value={form.outputMessageName} onChange={(value) => update("outputMessageName", value)} />
            </>
          )}
          <TextField label="Contract reference" value={form.contractUri} onChange={(value) => update("contractUri", value)} />
          <TextField label="Source code" value={form.sourceReference} onChange={(value) => update("sourceReference", value)} placeholder="Repository URL" />
          <TextField label="Source version" value={form.sourceRevision} onChange={(value) => update("sourceRevision", value)} hint="A tag or commit." />
        </div>
      </details>
    </>
  );
}

/* ------------------------------------------------------------------ Review */

export function ReviewStep({ form, nodeLabel, preview, checking, onRecheck, onEdit, evidence, onEvidence, acknowledged, onAcknowledge, catalogue }: {
  form: GuidedServiceForm; nodeLabel: string | null; preview: PreviewResponse | null; checking: boolean; onRecheck: () => void;
  onEdit: (step: "describe" | "connect") => void; evidence: Evidence; onEvidence: (key: keyof Evidence, value: boolean) => void;
  acknowledged: boolean; onAcknowledge: (value: boolean) => void; catalogue: CatalogueEntry[];
}) {
  const service = {
    name: form.name || "New service",
    description: form.description,
    operation_name: form.operationName,
    input_type: form.inputType,
    output_type: form.outputType,
    interface_contract: { design: { title: form.name, purpose: form.description } },
  };
  const text = serviceText(service);
  const ports = servicePorts(service);
  const stage = serviceStage(service, usable(catalogue));
  const icon = serviceIcon(service);
  const live = usable(catalogue);
  const takesLabel = form.inputType === WORKFLOW_START ? "Nothing (starts a workflow)"
    : (() => { const from = live.find((entry) => entry.output_type === form.inputType); return from ? `The result of ${serviceText(from).title}` : form.inputType; })();
  const producesLabel = form.outputType === WORKFLOW_OUTPUT ? "A final result (ends a workflow)"
    : (() => { const to = live.find((entry) => entry.input_type === form.outputType); return to ? `Data for ${serviceText(to).title}` : form.outputType; })();
  const errors = preview?.validation.filter((item) => item.level === "error") || [];
  const warnings = preview?.validation.filter((item) => item.level === "warning") || [];

  return (
    <>
      <h2 className="wizard-card__title">Check and submit</h2>
      <p className="wizard-card__lead">This is how your service will look to others once it is approved.</p>

      <div className="review-previews">
        <div>
          <span className="review-label">In the catalogue</span>
          <div className="palette-card review-card">
            <span className={`palette-card__icon flow-card__icon--${stage}`}><ServiceIcon kind={icon} /></span>
            <span className="palette-card__body">
              <span className="palette-card__top"><span className="palette-card__title">{text.title}</span></span>
              {form.version && <span className="palette-card__version">v{form.version.replace(/^v/i, "")}</span>}
              <span className="palette-card__purpose">{form.description || "No description yet."}</span>
              <span className="palette-card__tags">{nodeLabel && <span className="palette-card__node"><MapPin size={11} aria-hidden="true" />{nodeLabel}</span>}</span>
            </span>
          </div>
        </div>
        <div>
          <span className="review-label">In the Builder</span>
          <div className={`flow-card flow-card--${stage} review-card`}>
            <div className="flow-card__head">
              <span className={`flow-card__icon flow-card__icon--${stage}`}><ServiceIcon kind={icon} size={16} /></span>
              <span className="flow-card__title">{text.title}</span>
            </div>
            <div className="flow-card__meta">
              {form.version && <span className="flow-card__version">v{form.version.replace(/^v/i, "")}</span>}
              {nodeLabel && <span className="flow-card__node"><MapPin size={10} aria-hidden="true" />{nodeLabel}</span>}
            </div>
            <div className="flow-card__ports">
              <div className="flow-card__port flow-card__port--in"><span>{ports.input || "start"}</span></div>
              <div className="flow-card__port flow-card__port--out"><span>{ports.output}</span></div>
            </div>
          </div>
        </div>
      </div>

      <dl className="review-summary">
        <div><dt>Name</dt><dd>{form.name}</dd><button type="button" className="link-button" onClick={() => onEdit("describe")}>Edit</button></div>
        <div><dt>Takes</dt><dd>{takesLabel}</dd></div>
        <div><dt>Produces</dt><dd>{producesLabel}</dd></div>
        <div><dt>Called through</dt><dd>{INTERFACES.find((option) => option.key === form.interfaceType)?.title} · operation <code>{form.operationName}</code></dd><button type="button" className="link-button" onClick={() => onEdit("connect")}>Edit</button></div>
        <div><dt>Container</dt><dd><code>{form.image || form.dockerfile}</code> as <code>{form.containerName}:{form.internalPort}</code></dd></div>
        <div><dt>Catalogue ID</dt><dd><code>{form.serviceId}</code></dd></div>
      </dl>

      <div className={`review-check review-check--${checking ? "busy" : preview?.status || "busy"}`}>
        <strong>
          {checking ? "The platform is checking your service…"
            : !preview ? "Not checked yet"
            : preview.status === "invalid" ? <><TriangleAlert size={16} aria-hidden="true" /> A few things need fixing</>
            : preview.status === "warning" ? <><CircleCheck size={16} aria-hidden="true" /> Ready to submit, with notes</>
            : <><CircleCheck size={16} aria-hidden="true" /> Ready to submit</>}
        </strong>
        {errors.length > 0 && <ul>{errors.map((item) => <li key={item.message} className="is-error">{item.message}</li>)}</ul>}
        {warnings.length > 0 && (
          <details className="review-notes">
            <summary>{warnings.length} technical note{warnings.length === 1 ? "" : "s"} for the reviewer</summary>
            <ul>{warnings.map((item) => <li key={item.message}>{item.message}</li>)}</ul>
          </details>
        )}
        {!checking && <button type="button" className="link-button" onClick={onRecheck}>Check again</button>}
      </div>

      <fieldset className="review-evidence">
        <legend>Before you submit (optional, helps the review)</legend>
        <Tick checked={evidence.revisionPinned} onChange={(value) => onEvidence("revisionPinned", value)} text="The source version is fixed (a tag or commit)." />
        <Tick checked={evidence.imageReviewed} onChange={(value) => onEvidence("imageReviewed", value)} text="The image uses a fixed version tag." />
        <Tick checked={evidence.secretsExternal} onChange={(value) => onEvidence("secretsExternal", value)} text="No passwords or keys are built into the image." />
        <Tick checked={evidence.healthVerified} onChange={(value) => onEvidence("healthVerified", value)} text="The health check answers when the container runs." />
      </fieldset>
      <label className="review-ack">
        <input type="checkbox" checked={acknowledged} onChange={(event) => onAcknowledge(event.target.checked)} />
        <span>I understand that submitting adds the service for review. It does not start or deploy the container.</span>
      </label>
    </>
  );
}

function Tick({ checked, onChange, text }: { checked: boolean; onChange: (value: boolean) => void; text: string }) {
  return (
    <label className="review-tick">
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      <span className="review-tick__box" aria-hidden="true">{checked && <Check size={12} />}</span>
      <span>{text}</span>
    </label>
  );
}
