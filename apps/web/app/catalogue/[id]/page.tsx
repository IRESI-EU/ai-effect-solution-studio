import Link from "next/link";
import type { CSSProperties } from "react";

type Service = {
  id: string;
  name: string;
  description?: string | null;
  provider?: string | null;
  category?: string | null;
  version?: string | null;
  status?: string | null;
  trust_badge?: string | null;
  lifecycle_status?: string | null;

  input_type?: string | null;
  output_type?: string | null;

  container_name?: string | null;
  image?: string | null;
  proto_uri?: string | null;
  node_type?: string | null;
  operation_name?: string | null;
  input_message_name?: string | null;
  output_message_name?: string | null;
  internal_host?: string | null;
  internal_port?: string | null;

  repository_url?: string | null;
  repository_branch?: string | null;
  manifest_path?: string | null;
  interface_type?: string | null;
  interface_contract?: Record<string, unknown> | null;
  orchestration_mode?: string | null;
  adapter_type?: string | null;
  health_path?: string | null;
  contract_uri?: string | null;
};

async function getService(id: string): Promise<Service> {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:18080";

  const res = await fetch(`${apiBaseUrl}/services/${id}`, {
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error("Failed to load service");
  }

  return res.json();
}

export default async function ServiceDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const service = await getService(id);

  const interfaceType = service.interface_type || "control";
  const orchestrationMode = service.orchestration_mode || "native";
  const healthPath = service.health_path || "/health";

  return (
    <div className="page">
      <Link href="/catalogue" style={{ color: "#075985", fontWeight: 800 }}>
        ← Back to catalogue
      </Link>

      <section className="card" style={{ padding: 34, marginTop: 20 }}>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          <span className="badge">{service.trust_badge || "pending_review"}</span>
          <span style={lifecycleBadgeStyle(service.lifecycle_status || "active")}>
            {service.lifecycle_status || "active"}
          </span>
          <span style={interfaceBadgeStyle(interfaceType)}>{formatValue(interfaceType)}</span>
          <span style={orchestrationBadgeStyle(orchestrationMode)}>
            {formatValue(orchestrationMode)}
          </span>
          {service.adapter_type && (
            <span style={metadataBadgeStyle}>adapter: {service.adapter_type}</span>
          )}
        </div>

        <h1 style={{ fontSize: 42, marginBottom: 8 }}>{service.name}</h1>
        <p style={{ color: "#526173", fontSize: 18, maxWidth: 850, lineHeight: 1.7 }}>
          {service.description || "No description provided."}
        </p>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
          <Info title="Provider" value={service.provider || "Unknown"} />
          <Info title="Category" value={service.category || "Uncategorised"} />
          <Info title="Status" value={service.status || "pending_review"} />
          <Info title="Version" value={`v${service.version || "1.0.0"}`} />
        </div>
      </section>

      <section
        style={{
          display: "grid",
          gridTemplateColumns: "1.2fr 0.8fr",
          gap: 20,
          marginTop: 20,
        }}
      >
        <div className="card" style={{ padding: 28 }}>
          <h2>Interface contract</h2>
          <ContractRow label="Interface type" value={formatValue(interfaceType)} />
          <ContractRow label="Orchestration mode" value={formatValue(orchestrationMode)} />
          <ContractRow label="Adapter" value={service.adapter_type || "none"} />
          <ContractRow label="Input type" value={service.input_type || "Not specified"} />
          <ContractRow label="Output type" value={service.output_type || "Not specified"} />
          <ContractRow label="Operation" value={service.operation_name || "Not specified"} />
          <ContractRow label="Contract URI" value={service.contract_uri || "Not declared"} />
          <ContractRow label="Compatibility proto_uri" value={service.proto_uri || "Not declared"} />
          <ContractRow label="Health endpoint" value={healthPath} />
          <ContractRow label="Execute endpoint" value="/control/execute" />
          <ContractRow label="Status endpoint" value="/control/status/{id}" />
          <ContractRow label="Output endpoint" value="/control/output/{id}" />
        </div>

        <div className="card" style={{ padding: 28 }}>
          <h2>Runtime & source</h2>
          <ContractRow label="Container" value={service.container_name || "Not declared"} />
          <ContractRow label="Image" value={service.image || "Not declared"} />
          <ContractRow label="Internal host" value={service.internal_host || "Not declared"} />
          <ContractRow label="Internal port" value={service.internal_port || "Not declared"} />

          <h2 style={{ marginTop: 28 }}>Manifest source</h2>
          <ContractRow label="Repository" value={service.repository_url || "Not recorded"} />
          <ContractRow label="Branch" value={service.repository_branch || "Not recorded"} />
          <ContractRow label="Manifest path" value={service.manifest_path || "Not recorded"} />

          <h2 style={{ marginTop: 28 }}>Trust & readiness</h2>
          <Check text="Metadata available" />
          <Check text="Input/output declared" />
          <Check text="Dockerized service expected" />
          <Check text="Orchestrator validation pending" />

          <Link
            href="/builder"
            style={{
              display: "block",
              marginTop: 28,
              background: "#075985",
              color: "white",
              padding: "14px 18px",
              borderRadius: 12,
              textAlign: "center",
              fontWeight: 800,
            }}
          >
            Add to solution
          </Link>
        </div>
      </section>

      {service.interface_contract && (
        <section className="card" style={{ padding: 28, marginTop: 20 }}>
          <h2>Raw interface contract</h2>
          <pre
            style={{
              marginTop: 14,
              padding: 18,
              borderRadius: 14,
              background: "#0f172a",
              color: "#e2e8f0",
              overflowX: "auto",
              fontSize: 13,
              lineHeight: 1.5,
            }}
          >
            {JSON.stringify(service.interface_contract, null, 2)}
          </pre>
        </section>
      )}
    </div>
  );
}

function Info({ title, value }: { title: string; value: string }) {
  return (
    <div style={{ background: "#f8fafc", borderRadius: 14, padding: 16 }}>
      <div style={{ color: "#667085", fontSize: 13 }}>{title}</div>
      <strong>{value}</strong>
    </div>
  );
}

function ContractRow({ label, value }: { label: string; value: string }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "180px minmax(0, 1fr)",
        gap: 14,
        padding: 14,
        borderRadius: 12,
        background: "#f8fafc",
        marginTop: 12,
      }}
    >
      <strong>{label}</strong>
      <span style={{ color: "#526173", wordBreak: "break-word" }}>{value}</span>
    </div>
  );
}

function Check({ text }: { text: string }) {
  return (
    <div
      style={{
        padding: 12,
        borderRadius: 12,
        background: "#ecfdf3",
        color: "#067647",
        fontWeight: 700,
        marginTop: 12,
      }}
    >
      ✓ {text}
    </div>
  );
}

function formatValue(value?: string | null) {
  if (!value) return "Not specified";
  return value.replaceAll("_", " ");
}

const metadataBadgeStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  border: "1px solid #cbd5e1",
  borderRadius: 999,
  padding: "5px 9px",
  fontSize: 11,
  fontWeight: 800,
  textTransform: "uppercase",
  letterSpacing: "0.03em",
  background: "#ffffff",
  color: "#334155",
};

function lifecycleBadgeStyle(status: string): CSSProperties {
  if (status === "deprecated") {
    return {
      ...metadataBadgeStyle,
      background: "#fef3c7",
      color: "#92400e",
      borderColor: "#fde68a",
    };
  }

  if (status === "archived") {
    return {
      ...metadataBadgeStyle,
      background: "#f1f5f9",
      color: "#475569",
      borderColor: "#cbd5e1",
    };
  }

  return {
    ...metadataBadgeStyle,
    background: "#dcfce7",
    color: "#166534",
    borderColor: "#bbf7d0",
  };
}

function interfaceBadgeStyle(value?: string | null): CSSProperties {
  const normalized = value || "control";

  if (normalized === "grpc") {
    return {
      ...metadataBadgeStyle,
      background: "#eef2ff",
      color: "#3730a3",
      borderColor: "#c7d2fe",
    };
  }

  if (normalized === "http") {
    return {
      ...metadataBadgeStyle,
      background: "#ecfeff",
      color: "#0e7490",
      borderColor: "#a5f3fc",
    };
  }

  if (normalized === "container_job") {
    return {
      ...metadataBadgeStyle,
      background: "#f5f3ff",
      color: "#6d28d9",
      borderColor: "#ddd6fe",
    };
  }

  if (normalized === "legacy_sidecar") {
    return {
      ...metadataBadgeStyle,
      background: "#fff7ed",
      color: "#c2410c",
      borderColor: "#fed7aa",
    };
  }

  return {
    ...metadataBadgeStyle,
    background: "#f0fdf4",
    color: "#047857",
    borderColor: "#bbf7d0",
  };
}

function orchestrationBadgeStyle(value?: string | null): CSSProperties {
  const normalized = value || "native";

  if (normalized === "sidecar") {
    return {
      ...metadataBadgeStyle,
      background: "#fffbeb",
      color: "#92400e",
      borderColor: "#fde68a",
    };
  }

  if (normalized === "external") {
    return {
      ...metadataBadgeStyle,
      background: "#f8fafc",
      color: "#475569",
      borderColor: "#cbd5e1",
    };
  }

  if (normalized === "manual_review") {
    return {
      ...metadataBadgeStyle,
      background: "#fef2f2",
      color: "#b91c1c",
      borderColor: "#fecaca",
    };
  }

  return {
    ...metadataBadgeStyle,
    background: "#eff6ff",
    color: "#1d4ed8",
    borderColor: "#bfdbfe",
  };
}