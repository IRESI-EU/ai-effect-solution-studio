import type { CSSProperties } from "react";

type Service = {
  id: string;
  name: string;
  description?: string | null;
  provider?: string | null;
  category?: string | null;
  version?: string | null;
  trust_badge?: string | null;
  input_type?: string | null;
  output_type?: string | null;
  lifecycle_status?: "active" | "deprecated" | "archived" | string | null;

  repository_url?: string | null;
  repository_branch?: string | null;
  manifest_path?: string | null;
  interface_type?: string | null;
  orchestration_mode?: string | null;
  adapter_type?: string | null;
  health_path?: string | null;
  contract_uri?: string | null;
};

async function getServices(): Promise<Service[]> {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:18080";

  const res = await fetch(`${apiBaseUrl}/services`, {
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error("Failed to load services");
  }

  return res.json();
}

function getLifecycleStatus(service: Service) {
  return service.lifecycle_status || "active";
}

function formatInterfaceType(value?: string | null) {
  if (!value) return "control";
  return value.replaceAll("_", " ");
}

function formatOrchestrationMode(value?: string | null) {
  if (!value) return "native";
  return value.replaceAll("_", " ");
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

const metadataBadgeStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  border: "1px solid",
  borderRadius: 999,
  padding: "5px 9px",
  fontSize: 11,
  fontWeight: 800,
  textTransform: "uppercase",
  letterSpacing: "0.03em",
};

function lifecycleBadgeStyle(status: string): CSSProperties {
  if (status === "deprecated") {
    return {
      background: "#fef3c7",
      color: "#92400e",
      border: "1px solid #fde68a",
      padding: "6px 10px",
      borderRadius: 999,
      fontSize: 12,
      fontWeight: 800,
      textTransform: "uppercase",
      letterSpacing: 0.4,
    };
  }

  if (status === "archived") {
    return {
      background: "#f1f5f9",
      color: "#475569",
      border: "1px solid #cbd5e1",
      padding: "6px 10px",
      borderRadius: 999,
      fontSize: 12,
      fontWeight: 800,
      textTransform: "uppercase",
      letterSpacing: 0.4,
    };
  }

  return {
    background: "#dcfce7",
    color: "#166534",
    border: "1px solid #bbf7d0",
    padding: "6px 10px",
    borderRadius: 999,
    fontSize: 12,
    fontWeight: 800,
    textTransform: "uppercase",
    letterSpacing: 0.4,
  };
}

export default async function CataloguePage() {
  const services = await getServices();

  const activeCount = services.filter((service) => getLifecycleStatus(service) === "active").length;
  const deprecatedCount = services.filter(
    (service) => getLifecycleStatus(service) === "deprecated"
  ).length;

  return (
    <div className="page">
      <div style={{ display: "flex", justifyContent: "space-between", gap: 24 }}>
        <div>
          <span className="badge">Service Marketplace</span>
          <h1 style={{ fontSize: 40, marginBottom: 8 }}>Discover AI-EFFECT services</h1>
          <p style={{ color: "#526173", fontSize: 17 }}>
            Browse trusted, Dockerized AI services published by AI-EFFECT nodes.
          </p>
        </div>

        <div
          className="card"
          style={{
            padding: 18,
            minWidth: 260,
            alignSelf: "flex-start",
            display: "grid",
            gap: 10,
          }}
        >
          <strong>Catalogue status</strong>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 14 }}>
            <span style={{ color: "#526173" }}>Active services</span>
            <strong>{activeCount}</strong>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 14 }}>
            <span style={{ color: "#526173" }}>Deprecated services</span>
            <strong>{deprecatedCount}</strong>
          </div>
          <p style={{ color: "#667085", fontSize: 13, margin: 0, lineHeight: 1.5 }}>
            Archived services are hidden from the catalogue and cannot be added to new workflow
            submissions.
          </p>
        </div>
      </div>

      {deprecatedCount > 0 && (
        <div
          className="card"
          style={{
            marginTop: 24,
            padding: 18,
            border: "1px solid #fde68a",
            background: "#fffbeb",
          }}
        >
          <strong style={{ color: "#92400e" }}>Deprecated services are present</strong>
          <p style={{ color: "#92400e", margin: "8px 0 0", lineHeight: 1.6 }}>
            Deprecated services remain available for compatibility, but they should be avoided for
            new solution designs where an active replacement exists.
          </p>
        </div>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
          gap: 20,
          marginTop: 28,
        }}
      >
        {services.map((service) => {
          const lifecycleStatus = getLifecycleStatus(service);
          const isDeprecated = lifecycleStatus === "deprecated";

          return (
            <div
              className="card"
              key={service.id}
              style={{
                padding: 24,
                border: isDeprecated ? "1px solid #fde68a" : undefined,
                background: isDeprecated ? "#fffdf7" : undefined,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                <span className="badge">{service.trust_badge || "Trusted"}</span>
                <span style={{ color: "#667085", fontSize: 13 }}>
                  v{service.version || "1.0.0"}
                </span>
              </div>

              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 12,
                  alignItems: "flex-start",
                  marginTop: 14,
                }}
              >
                <h2 style={{ margin: 0 }}>{service.name}</h2>
                <span style={lifecycleBadgeStyle(lifecycleStatus)}>{lifecycleStatus}</span>
              </div>

              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 12 }}>
                <span style={interfaceBadgeStyle(service.interface_type)}>
                  {formatInterfaceType(service.interface_type)}
                </span>

                <span style={orchestrationBadgeStyle(service.orchestration_mode)}>
                  {formatOrchestrationMode(service.orchestration_mode)}
                </span>

                {service.adapter_type && (
                  <span style={metadataBadgeStyle}>adapter: {service.adapter_type}</span>
                )}

                {service.contract_uri && (
                  <span style={metadataBadgeStyle}>contract: {service.contract_uri}</span>
                )}
              </div>

              {isDeprecated && (
                <div
                  style={{
                    marginTop: 12,
                    padding: 12,
                    borderRadius: 12,
                    background: "#fef3c7",
                    color: "#92400e",
                    fontSize: 13,
                    lineHeight: 1.5,
                    fontWeight: 600,
                  }}
                >
                  This service is deprecated. Existing solutions may still use it, but new designs
                  should prefer an active replacement.
                </div>
              )}

              <p style={{ color: "#526173", lineHeight: 1.6, minHeight: 78 }}>
                {service.description || "No description provided."}
              </p>

              <div style={{ display: "grid", gap: 8, marginTop: 18, fontSize: 14 }}>
                <div>
                  <strong>Provider:</strong> {service.provider || "Unknown"}
                </div>
                <div>
                  <strong>Category:</strong> {service.category || "Uncategorised"}
                </div>
                <div>
                  <strong>Input:</strong> {service.input_type || "Not specified"}
                </div>
                <div>
                  <strong>Output:</strong> {service.output_type || "Not specified"}
                </div>
              </div>

              <div style={{ display: "flex", gap: 10, marginTop: 22 }}>
                <a
                  href={`/catalogue/${service.id}`}
                  style={{
                    background: "#075985",
                    color: "white",
                    padding: "10px 14px",
                    borderRadius: 10,
                    fontWeight: 700,
                  }}
                >
                  View details
                </a>
                <a
                  href="/builder"
                  style={{
                    border: "1px solid #bae6fd",
                    color: "#075985",
                    padding: "10px 14px",
                    borderRadius: 10,
                    fontWeight: 700,
                  }}
                >
                  Add to solution
                </a>
              </div>
            </div>
          );
        })}
      </div>

      {services.length === 0 && (
        <div className="card" style={{ padding: 24, marginTop: 28 }}>
          <h2>No catalogue services available</h2>
          <p style={{ color: "#526173" }}>
            No active or deprecated services are currently visible. Archived services can be managed
            from Admin Governance.
          </p>
        </div>
      )}
    </div>
  );
}