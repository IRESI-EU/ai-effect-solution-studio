"use client";

import { CircleAlert, CircleCheck, TriangleAlert, Upload } from "lucide-react";
import { useState } from "react";

type Operation = { operation_name: string; input_message_name: string; output_message_name: string; compatible_with_proto: boolean; compatibility_message: string };
type Service = {
  key: string; proposed_id: string; name: string; description: string; category: string; version: string;
  container_name: string; image: string; internal_host?: string | null; internal_port?: string | null;
  node_type: string; proto_path: string; operations: Operation[]; selected_operation?: string | null;
  duplicate_conflicts: string[]; blockers: string[];
};
type Preview = {
  upload_token: string; package_name: string; archive_name: string; services: Service[];
  connections: Array<{ source_service: string; source_operation: string; target_service: string; target_operation: string }>;
  warnings: string[]; registration_status: string; runtime_status: string; operation_compatibility: string;
};
type Editable = Service & { selected: boolean; operation_name: string; health_path: string; register_incomplete_draft: boolean };

export function PackageImportPanel() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [services, setServices] = useState<Editable[]>([]);
  const [createSolution, setCreateSolution] = useState(false);
  const [solutionName, setSolutionName] = useState("");
  const [acknowledged, setAcknowledged] = useState(false);
  const [busy, setBusy] = useState<"preview" | "confirm" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);

  async function inspectPackage() {
    if (!file) return;
    setBusy("preview"); setError(null); setPreview(null); setResult(null);
    const body = new FormData(); body.append("file", file);
    try {
      const response = await fetch("/api/services/import/package/preview", { method: "POST", body });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(formatError(data.detail) || "Package inspection failed.");
      const typed = data as Preview;
      setPreview(typed); setSolutionName(typed.package_name);
      setServices(typed.services.map((service) => ({ ...service, selected: service.duplicate_conflicts.length === 0, operation_name: service.selected_operation || "", health_path: "/health", register_incomplete_draft: false })));
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Package inspection failed."); }
    finally { setBusy(null); }
  }

  function edit(key: string, field: keyof Editable, value: string | boolean) {
    setServices((current) => current.map((service) => service.key === key ? { ...service, [field]: value } : service));
    setResult(null); setAcknowledged(false);
  }

  async function confirm() {
    if (!preview) return;
    setBusy("confirm"); setError(null); setResult(null);
    try {
      const response = await fetch("/api/services/import/package/confirm", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          upload_token: preview.upload_token, create_solution: createSolution,
          solution_name: solutionName, registration_only_acknowledged: acknowledged,
          services: services.map((service) => ({
            key: service.key, selected: service.selected, service_id: service.proposed_id,
            name: service.name, description: service.description, category: service.category,
            operation_name: service.operation_name, internal_host: service.internal_host || null,
            internal_port: service.internal_port || null, health_path: service.health_path,
            register_incomplete_draft: service.register_incomplete_draft,
          })),
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(formatError(data.detail) || "Package registration failed.");
      setResult(data);
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Package registration failed."); }
    finally { setBusy(null); }
  }

  const selectedKeys = new Set(services.filter((service) => service.selected).map((service) => service.key));
  const unresolved = preview?.connections.filter((edge) => selectedKeys.has(edge.source_service) !== selectedKeys.has(edge.target_service)) || [];
  const selectedBlocked = services.some((service) => service.selected && (service.duplicate_conflicts.length > 0 || !service.operation_name || service.operations.find((operation) => operation.operation_name === service.operation_name)?.compatible_with_proto !== true));

  return <div className="package-flow">
    <label
      className={`drop-zone drop-zone--package${file ? " has-file" : ""}`}
      onDragOver={(event) => event.preventDefault()}
      onDrop={(event) => { event.preventDefault(); const dropped = event.dataTransfer.files?.[0]; if (dropped) { setFile(dropped); setPreview(null); setResult(null); setError(null); } }}
    >
      <Upload size={20} aria-hidden="true" />
      <div>
        <strong>{file ? file.name : "Drop your package ZIP here, or click to choose it"}</strong>
        <span>{file ? `${(file.size / 1024 / 1024).toFixed(2)} MB` : "It should contain blueprint.json, dockerinfo.json and the microservice .proto files."}</span>
      </div>
      <input type="file" accept=".zip,application/zip" hidden onChange={(event) => { setFile(event.target.files?.[0] || null); setPreview(null); setResult(null); setError(null); }} />
    </label>
    <button type="button" className="ae-btn ae-btn--primary" disabled={!file || busy !== null} onClick={inspectPackage}>{busy === "preview" ? "Reading the package…" : "Read the package"}</button>
    <p className="muted package-note">Nothing is built or started: the package is only read to fill in the catalogue entries.</p>

    {preview && <div className="package-preview">
      <h3 className="wizard-section">{preview.package_name}: {services.length} service{services.length === 1 ? "" : "s"} found</h3>
      <p className="wizard-card__lead">Tick the services to add. Names and descriptions are what others will see; the technical details came from the package.</p>
      {preview.warnings.map((warning) => <p key={warning} className="wizard-note"><TriangleAlert size={15} aria-hidden="true" /> {warning}</p>)}
      <div className="package-service-list">
        {services.map((service) => {
          const problems = [...service.blockers, ...service.duplicate_conflicts];
          return <section key={service.key} className={`package-service${service.selected ? " is-selected" : ""}`}>
            <label className="package-service__pick">
              <input type="checkbox" checked={service.selected} onChange={(e) => edit(service.key, "selected", e.target.checked)} />
              <span><strong>{service.name || service.container_name}</strong><small>{service.image}</small></span>
            </label>
            {service.selected && <>
              <div className="wizard-grid">
                <label className="wizard-field"><span className="wizard-field__label">Name</span><input className="ae-input" value={service.name} onChange={(e) => edit(service.key, "name", e.target.value)} /></label>
                <label className="wizard-field"><span className="wizard-field__label">Operation</span><select className="ae-input" value={service.operation_name} onChange={(e) => edit(service.key, "operation_name", e.target.value)}><option value="">Choose one</option>{service.operations.map((operation) => <option key={operation.operation_name} value={operation.operation_name} disabled={!operation.compatible_with_proto}>{operation.operation_name} ({operation.input_message_name} → {operation.output_message_name})</option>)}</select></label>
                <label className="wizard-field wizard-field--wide"><span className="wizard-field__label">What does it do?</span><textarea className="ae-input" rows={3} value={service.description} onChange={(e) => edit(service.key, "description", e.target.value)} placeholder="One to three sentences for researchers from other nodes." />{/^imported from/i.test(service.description.trim()) && <small>Replace this with what the service does, so others can find it.</small>}</label>
              </div>
              <details className="wizard-advanced">
                <summary>Technical details from the package</summary>
                <div className="wizard-grid">
                  <label className="wizard-field"><span className="wizard-field__label">Catalogue ID</span><input className="ae-input" value={service.proposed_id} onChange={(e) => edit(service.key, "proposed_id", e.target.value)} /></label>
                  <label className="wizard-field"><span className="wizard-field__label">Category</span><input className="ae-input" value={service.category} onChange={(e) => edit(service.key, "category", e.target.value)} /></label>
                  <label className="wizard-field"><span className="wizard-field__label">Network host</span><input className="ae-input" value={service.internal_host || ""} onChange={(e) => edit(service.key, "internal_host", e.target.value)} /></label>
                  <label className="wizard-field"><span className="wizard-field__label">Port</span><input className="ae-input" value={service.internal_port || ""} onChange={(e) => edit(service.key, "internal_port", e.target.value)} /></label>
                  <label className="wizard-field"><span className="wizard-field__label">Health check path</span><input className="ae-input" value={service.health_path} onChange={(e) => edit(service.key, "health_path", e.target.value)} /></label>
                  <div className="wizard-field"><span className="wizard-field__label">Contract</span><code>{service.proto_path}</code></div>
                </div>
              </details>
              {problems.length > 0 && <ul className="wizard-problems">{problems.map((message) => <li key={message}><CircleAlert size={14} aria-hidden="true" /> {message}</li>)}</ul>}
              {(!service.internal_host || !service.internal_port) && <label className="review-ack"><input type="checkbox" checked={service.register_incomplete_draft} onChange={(e) => edit(service.key, "register_incomplete_draft", e.target.checked)} /><span>The package has no network address for this service. Add it as an unfinished draft; it cannot run until the address is added.</span></label>}
            </>}
          </section>;
        })}
      </div>
      {preview.connections.length > 0 && <>
        <label className="review-ack"><input type="checkbox" checked={createSolution} onChange={(e) => setCreateSolution(e.target.checked)} /><span>Also create a draft solution from the package&apos;s {preview.connections.length} connection{preview.connections.length === 1 ? "" : "s"}.</span></label>
        {createSolution && <><label className="wizard-field"><span className="wizard-field__label">Solution name</span><input className="ae-input" value={solutionName} onChange={(e) => setSolutionName(e.target.value)} /></label>{unresolved.length > 0 && <p className="wizard-error"><CircleAlert size={15} aria-hidden="true" /> Tick both ends of every connection ({unresolved.length} open), or turn this option off.</p>}</>}
      </>}
      <label className="review-ack"><input type="checkbox" checked={acknowledged} onChange={(e) => setAcknowledged(e.target.checked)} /><span>I understand that submitting adds these services for review. It does not start or deploy any container.</span></label>
      <button type="button" className="ae-btn ae-btn--primary" disabled={!acknowledged || selectedBlocked || selectedKeys.size === 0 || (createSolution && unresolved.length > 0) || busy !== null} onClick={confirm}>{busy === "confirm" ? "Submitting…" : `Submit ${selectedKeys.size} service${selectedKeys.size === 1 ? "" : "s"} for review`}</button>
    </div>}
    {error && <p className="wizard-error" role="alert"><CircleAlert size={15} aria-hidden="true" /> {error}</p>}
    {result && <div className="review-check review-check--valid"><strong><CircleCheck size={16} aria-hidden="true" /> {result.message}</strong><p>{result.services?.map((service: { name: string }) => service.name).join(", ")}</p>{result.solution && <p>Draft solution created: {result.solution.name}</p>}<p className="muted">An administrator reviews them next; once approved they appear in the catalogue.</p></div>}
  </div>;
}

function formatError(detail: unknown) { if (typeof detail === "string") return detail; if (Array.isArray(detail)) return detail.map(String).join(" "); return detail ? JSON.stringify(detail) : ""; }
