"use client";

import { useEffect, useMemo, useState, type CSSProperties } from "react";

export type ManagedRuntimeService = {
  id: string;
  name: string;
  container_name?: string | null;
  internal_host?: string | null;
  internal_port?: string | null;
  health_path?: string | null;
  operation_name?: string | null;
  input_message_name?: string | null;
  output_message_name?: string | null;
  contract_uri?: string | null;
  proto_uri?: string | null;
  interface_contract?: {
    runtime_verification?: RuntimeVerification;
  } | null;
};

type RuntimeVerification = {
  status?: "verified" | "failed" | "not_verified";
  checked_at?: string | null;
  invalidated_at?: string | null;
  runtime_url?: string | null;
  http_status?: number | null;
  failure_reason?: string | null;
  message?: string;
};

type Draft = {
  internal_host: string;
  internal_port: string;
  health_path: string;
  operation_name: string;
  input_message_name: string;
  output_message_name: string;
  contract_uri: string;
  proto_uri: string;
};

export function ServiceRuntimeManager({
  service,
  onUpdated,
}: {
  service: ManagedRuntimeService;
  onUpdated: () => Promise<void> | void;
}) {
  const [draft, setDraft] = useState<Draft>(() => fromService(service));
  const [busy, setBusy] = useState<"save" | "verify" | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const verification = service.interface_contract?.runtime_verification;
  const healthUrl = useMemo(
    () => runtimeUrl(draft.internal_host, draft.internal_port, draft.health_path),
    [draft.internal_host, draft.internal_port, draft.health_path],
  );

  useEffect(() => setDraft(fromService(service)), [service]);

  function edit(field: keyof Draft, value: string) {
    setDraft((current) => ({ ...current, [field]: value }));
    setNotice(null);
    setError(null);
  }

  async function save() {
    setBusy("save");
    setNotice(null);
    setError(null);
    try {
      const response = await fetch(`/api/services/${service.id}/technical-metadata`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(draft),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(formatError(data.detail) || "Could not save technical metadata.");
      setNotice("Saved. Previous runtime verification was invalidated; verify the connection again.");
      await onUpdated();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save technical metadata.");
    } finally {
      setBusy(null);
    }
  }

  async function verify() {
    setBusy("verify");
    setNotice(null);
    setError(null);
    try {
      const response = await fetch(`/api/services/${service.id}/runtime/verify`, { method: "POST" });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(formatError(data.detail) || "Runtime verification failed.");
      const result = data as RuntimeVerification;
      if (result.status === "verified") {
        setNotice(`Connectivity verified: ${result.runtime_url} returned HTTP ${result.http_status}.`);
      } else {
        setError(`${result.message}${result.failure_reason ? ` (${result.failure_reason})` : ""}`);
      }
      await onUpdated();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Runtime verification failed.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <details style={cardStyle}>
      <summary style={{ cursor: "pointer", fontWeight: 850 }}>
        {service.name} <span style={{ color: "#667085", fontFamily: "monospace", fontWeight: 500 }}>({service.id})</span>
      </summary>
      <div style={{ marginTop: 14 }}>
        <p style={{ color: "#667085", marginTop: 0 }}>
          Logical WP3 identity: <code>{service.container_name || "not set"}</code>. Configured health URL: <code>{healthUrl}</code>
        </p>
        <div style={gridStyle}>
          <Field label="Runtime network host" value={draft.internal_host} onChange={(value) => edit("internal_host", value)} help="The hostname reachable from the platform network. It may differ from the logical service name." />
          <Field label="Internal port" value={draft.internal_port} onChange={(value) => edit("internal_port", value)} />
          <Field label="Health path" value={draft.health_path} onChange={(value) => edit("health_path", value)} />
          <Field label="Operation name" value={draft.operation_name} onChange={(value) => edit("operation_name", value)} />
          <Field label="Input message name" value={draft.input_message_name} onChange={(value) => edit("input_message_name", value)} />
          <Field label="Output message name" value={draft.output_message_name} onChange={(value) => edit("output_message_name", value)} />
          <Field label="Contract reference" value={draft.contract_uri} onChange={(value) => edit("contract_uri", value)} />
          <Field label="WP3 proto reference" value={draft.proto_uri} onChange={(value) => edit("proto_uri", value)} />
        </div>
        <div style={{ display: "flex", gap: 9, flexWrap: "wrap", marginTop: 13 }}>
          <button type="button" disabled={busy !== null} onClick={save} style={buttonStyle}>{busy === "save" ? "Saving…" : "Save technical metadata"}</button>
          <button type="button" disabled={busy !== null} onClick={verify} style={{ ...buttonStyle, background: "#047857" }}>{busy === "verify" ? "Checking from API network…" : "Verify runtime connection"}</button>
        </div>
        <div style={{ marginTop: 12, padding: 12, borderRadius: 10, background: verification?.status === "verified" ? "#ecfdf3" : "#fffaeb", color: verification?.status === "verified" ? "#027a48" : "#92400e" }}>
          <strong>{verification?.status === "verified" ? "Connectivity verified" : verification?.status === "failed" ? "Verification failed" : "Not currently verified"}</strong>
          <div style={{ marginTop: 4 }}>{verification?.message || "Run verification from the portal API network before treating this service as runnable."}</div>
          <small style={{ display: "block", marginTop: 5 }}>A successful health response proves network connectivity only; it does not prove that the operation contract or output is correct.</small>
        </div>
        {notice && <p style={{ color: "#027a48", fontWeight: 750 }}>{notice}</p>}
        {error && <p style={{ color: "#b42318", fontWeight: 750 }}>{error}</p>}
      </div>
    </details>
  );
}

function fromService(service: ManagedRuntimeService): Draft {
  return {
    internal_host: service.internal_host || service.container_name || "",
    internal_port: service.internal_port || "8080",
    health_path: service.health_path || "/health",
    operation_name: service.operation_name || "",
    input_message_name: service.input_message_name || "Request",
    output_message_name: service.output_message_name || "Response",
    contract_uri: service.contract_uri || "",
    proto_uri: service.proto_uri || service.contract_uri || "",
  };
}

function runtimeUrl(host: string, port: string, path: string) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${host.includes("://") ? host : `http://${host}`}:${port}${normalizedPath}`;
}

function Field({ label, value, onChange, help }: { label: string; value: string; onChange: (value: string) => void; help?: string }) {
  return <label style={{ display: "grid", gap: 6, fontSize: 12, fontWeight: 750 }}>{label}<input value={value} onChange={(event) => onChange(event.target.value)} style={{ border: "1px solid #cbd5e1", borderRadius: 9, padding: "9px 10px" }} />{help && <small style={{ color: "#667085", fontWeight: 500 }}>{help}</small>}</label>;
}

function formatError(detail: unknown) {
  if (typeof detail === "string") return detail;
  return detail ? JSON.stringify(detail) : "";
}

const cardStyle: CSSProperties = { border: "1px solid #ddd8f4", borderRadius: 13, padding: 14, background: "#fff" };
const gridStyle: CSSProperties = { display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(210px,1fr))", gap: 11 };
const buttonStyle: CSSProperties = { border: 0, borderRadius: 9, padding: "9px 12px", background: "#5b2cf2", color: "white", fontWeight: 800, cursor: "pointer" };
