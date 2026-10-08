"use client";

import { useState, type CSSProperties } from "react";

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

  return <div className="guided-form">
    <div className="package-expectation">
      <strong>Prepared AI4EU/WP3 package</strong>
      <p>Upload a ZIP containing <code>blueprint.json</code>, <code>dockerinfo.json</code>, and <code>microservice/*.proto</code>, either at the archive root or inside one enclosing folder.</p>
      <p>This importer does not accept arbitrary source-code ZIPs and does not build images, run Docker Compose, start containers, or generate adapters.</p>
    </div>
    <label style={labelStyle}>Service package (.zip)<input type="file" accept=".zip,application/zip" onChange={(event) => { setFile(event.target.files?.[0] || null); setPreview(null); setResult(null); setError(null); }} style={inputStyle} /></label>
    {file && <small>{file.name} · {(file.size / 1024 / 1024).toFixed(2)} MiB</small>}
    <button type="button" style={primaryButtonStyle} disabled={!file || busy !== null} onClick={inspectPackage}>{busy === "preview" ? "Inspecting safely…" : "Inspect package"}</button>

    {preview && <div className="package-preview">
      <div className="package-status-grid">
        <Status label="Registration" value={preview.registration_status} />
        <Status label="Runtime verification" value="Unverified declarations" />
        <Status label="Operation compatibility" value={preview.operation_compatibility} />
      </div>
      <h3>{preview.package_name}</h3>
      {preview.warnings.map((warning) => <p key={warning} className="package-warning">{warning}</p>)}
      <p>Review every detected service. Runtime addresses came from the package and remain unverified until checked from the platform API network.</p>
      <div className="package-service-list">
        {services.map((service) => <section key={service.key} className="package-service-card">
          <label className="package-service-select"><input type="checkbox" checked={service.selected} onChange={(e) => edit(service.key, "selected", e.target.checked)} /><strong>{service.container_name}</strong><span>{service.image}</span></label>
          <div className="guided-grid">
            <Field label="Catalogue service ID" value={service.proposed_id} onChange={(value) => edit(service.key, "proposed_id", value)} />
            <Field label="Catalogue name" value={service.name} onChange={(value) => edit(service.key, "name", value)} />
            <Field label="Category" value={service.category} onChange={(value) => edit(service.key, "category", value)} />
            <Field label="Runtime network host" value={service.internal_host || ""} onChange={(value) => edit(service.key, "internal_host", value)} />
            <Field label="Runtime port" value={service.internal_port || ""} onChange={(value) => edit(service.key, "internal_port", value)} />
            <Field label="Health path" value={service.health_path} onChange={(value) => edit(service.key, "health_path", value)} />
            <label style={labelStyle}>Supported operation<select value={service.operation_name} onChange={(e) => edit(service.key, "operation_name", e.target.value)} style={inputStyle}><option value="">Select explicitly</option>{service.operations.map((operation) => <option key={operation.operation_name} value={operation.operation_name} disabled={!operation.compatible_with_proto}>{operation.operation_name} ({operation.input_message_name} → {operation.output_message_name})</option>)}</select></label>
            <label style={{ ...labelStyle, gridColumn: "1 / -1" }}>Description<textarea value={service.description} onChange={(e) => edit(service.key, "description", e.target.value)} style={{ ...inputStyle, minHeight: 74 }} /></label>
          </div>
          <p><strong>Declared health URL:</strong> <code>http://{service.internal_host || "missing-host"}:{service.internal_port || "missing-port"}{service.health_path.startsWith("/") ? service.health_path : `/${service.health_path}`}</code> · not verified</p>
          <details><summary>All detected operations and contract</summary>{service.operations.map((operation) => <p key={operation.operation_name}><strong>{operation.operation_name}</strong>: {operation.input_message_name} → {operation.output_message_name} · {operation.compatibility_message}</p>)}<p>Protobuf: <code>{service.proto_path}</code></p></details>
          {(service.blockers.length > 0 || service.duplicate_conflicts.length > 0) && <div className="package-errors">{[...service.blockers, ...service.duplicate_conflicts].map((message) => <p key={message}>{message}</p>)}</div>}
          {(!service.internal_host || !service.internal_port) && <label className="onboarding-acknowledgement"><input type="checkbox" checked={service.register_incomplete_draft} onChange={(e) => edit(service.key, "register_incomplete_draft", e.target.checked)} /><span>Register this as an incomplete draft for later runtime completion. It will not be runnable.</span></label>}
        </section>)}
      </div>
      {preview.connections.length > 0 && <details open><summary>Detected pipeline connections ({preview.connections.length})</summary>{preview.connections.map((edge, index) => <p key={`${edge.source_service}-${index}`}><code>{edge.source_service}:{edge.source_operation}</code> → <code>{edge.target_service}:{edge.target_operation}</code></p>)}</details>}
      <label className="onboarding-acknowledgement"><input type="checkbox" checked={createSolution} onChange={(e) => setCreateSolution(e.target.checked)} /><span>Also create a draft solution from these connections.</span></label>
      {createSolution && <><Field label="Draft solution name" value={solutionName} onChange={setSolutionName} />{unresolved.length > 0 && <div className="package-errors">A draft solution cannot be created while selected services leave {unresolved.length} unresolved connection(s). Select both sides or turn this option off.</div>}</>}
      <label className="onboarding-acknowledgement"><input type="checkbox" checked={acknowledged} onChange={(e) => setAcknowledged(e.target.checked)} /><span>I understand this creates pending-review catalogue records only; it does not deploy or activate containers.</span></label>
      <button type="button" style={primaryButtonStyle} disabled={!acknowledged || selectedBlocked || selectedKeys.size === 0 || (createSolution && unresolved.length > 0) || busy !== null} onClick={confirm}>{busy === "confirm" ? "Registering atomically…" : "Submit selected services for approval"}</button>
    </div>}
    {error && <div className="package-errors">{error}</div>}
    {result && <div className="package-success"><strong>{result.message}</strong><p>{result.services?.map((service: any) => service.name).join(", ")}</p>{result.solution && <p>Draft solution created: {result.solution.name}</p>}</div>}
  </div>;
}

function Status({ label, value }: { label: string; value: string }) { return <div><span>{label}</span><strong>{value}</strong></div>; }
function Field({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) { return <label style={labelStyle}>{label}<input value={value} onChange={(e) => onChange(e.target.value)} style={inputStyle} /></label>; }
function formatError(detail: unknown) { if (typeof detail === "string") return detail; if (Array.isArray(detail)) return detail.map(String).join(" "); return detail ? JSON.stringify(detail) : ""; }

const labelStyle: CSSProperties = { display: "flex", flexDirection: "column", gap: 7, fontSize: 13, fontWeight: 750, color: "#334155" };
const inputStyle: CSSProperties = { width: "100%", border: "1px solid #cbd5e1", borderRadius: 11, padding: "10px 11px", fontSize: 14, background: "#fff", boxSizing: "border-box" };
const primaryButtonStyle: CSSProperties = { marginTop: 14, border: 0, borderRadius: 11, padding: "11px 16px", color: "#fff", background: "linear-gradient(135deg,#5b2cf2,#4320ca)", fontWeight: 800, cursor: "pointer" };
