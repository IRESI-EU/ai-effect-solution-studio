import type { CSSProperties } from "react";
import Link from "next/link";
import { ArrowRight, Boxes, Building2, Search, SlidersHorizontal } from "lucide-react";

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
  operation_name?: string | null;
  node_type?: string | null;
};

type ServicePresentation = {
  displayName: string;
  purpose: string;
  stage: string;
};

const operationPresentation: Record<string, ServicePresentation> = {
  BuildRunConfig: {
    displayName: "SYSLAB configuration assistant",
    purpose: "Turns a plain-language district-heating request into a structured run configuration for topology generation.",
    stage: "1 · Configure the scenario",
  },
  GenerateTopology: {
    displayName: "District-heating topology generator",
    purpose: "Generates feasible SYSLAB network candidates from a validated supply, load, and routing configuration.",
    stage: "2 · Generate candidate networks",
  },
  RenderTopologies: {
    displayName: "Topology drawing service",
    purpose: "Renders generated network candidates as SVG diagrams so operators can review and compare the options.",
    stage: "3 · Review visual results",
  },
  ConfigureAndSynthesize: {
    displayName: "Synthetic grid generator",
    purpose: "Creates a reproducible pandapower grid model for testing network-optimisation algorithms.",
    stage: "1 · Generate a test grid",
  },
  RunBenchmark: {
    displayName: "Grid optimisation benchmark",
    purpose: "Runs a Grid2Op benchmark against a supplied grid and reports scenario-level and aggregate performance indicators.",
    stage: "2 · Evaluate an algorithm",
  },
  GetConfiguration: {
    displayName: "Energy pipeline configuration",
    purpose: "Provides the run configuration used to start the Portuguese synthetic energy-data demonstration.",
    stage: "1 · Prepare the run",
  },
  GenerateData: {
    displayName: "Synthetic energy data generator",
    purpose: "Produces a repeatable household energy dataset for downstream analysis and reporting.",
    stage: "2 · Generate energy data",
  },
  AnalyzeData: {
    displayName: "Energy efficiency analyser",
    purpose: "Analyses an upstream energy CSV for efficiency indicators and potential anomalies.",
    stage: "3 · Analyse the dataset",
  },
  GenerateReport: {
    displayName: "Energy analysis report",
    purpose: "Summarises analysed energy data into a compact report of anomalies, efficiency, and power statistics.",
    stage: "4 · Produce the report",
  },
};

function getServicePresentation(service: Service): ServicePresentation {
  const nameParts = service.name.split("/");
  const operation =
    service.operation_name || nameParts[nameParts.length - 1]?.trim() || "";
  return operationPresentation[operation] || {
    displayName: service.name,
    purpose: service.description || "Technical service metadata is available while the provider description is being completed.",
    stage: service.node_type
      ? service.node_type.replaceAll("_", " ")
      : "Workflow service",
  };
}

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

export default async function CataloguePage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; category?: string; provider?: string }>;
}) {
  const services = await getServices();
  const filters = await searchParams;
  const query = (filters.q || "").trim().toLowerCase();

  const activeCount = services.filter((service) => getLifecycleStatus(service) === "active").length;
  const deprecatedCount = services.filter(
    (service) => getLifecycleStatus(service) === "deprecated"
  ).length;
  const archivedCount = services.filter(
    (service) => getLifecycleStatus(service) === "archived"
  ).length;
  const categories = [...new Set(services.map((service) => service.category).filter(Boolean))] as string[];
  const providers = [...new Set(services.map((service) => service.provider).filter(Boolean))] as string[];
  const visibleServices = services.filter((service) => {
    const searchable = [service.name, service.description, service.provider, service.category]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();

    return (
      (!query || searchable.includes(query)) &&
      (!filters.category || service.category === filters.category) &&
      (!filters.provider || service.provider === filters.provider)
    );
  });
  const hasFilters = Boolean(filters.q || filters.category || filters.provider);

  return (
    <div className="page">
      <div className="catalogue-page-header">
        <div>
          <span className="badge">Service Marketplace</span>
          <h1 style={{ margin: "14px 0 8px", fontSize: 42, letterSpacing: "-0.04em" }}>Find the right service for your energy AI workflow</h1>
          <p style={{ maxWidth: 700, margin: 0, color: "#626a83", fontSize: 16, lineHeight: 1.65 }}>
            Understand what each service does, what it needs, and where it fits before adding it to a solution.
          </p>
        </div>

        <div className="card catalogue-status-card" style={{ padding: 19 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 9, marginBottom: 14 }}>
            <div style={{ display: "grid", width: 34, height: 34, placeItems: "center", borderRadius: 10, background: "#f0ecff", color: "#6240dd" }}><Boxes size={18} /></div>
            <div><strong style={{ display: "block", fontSize: 13 }}>Catalogue status</strong><span style={{ color: "#7a7f94", fontSize: 9 }}>Live service registry</span></div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8 }}>
            <StatusMetric label="Active" value={activeCount} color="#178055" background="#eaf8f1" />
            <StatusMetric label="Deprecated" value={deprecatedCount} color="#a86711" background="#fff5e5" />
            <StatusMetric label="Archived" value={archivedCount} color="#5e6477" background="#f1f2f5" />
          </div>
          <p style={{ margin: "13px 0 0", color: "#777c90", fontSize: 10, lineHeight: 1.5 }}>Archived services remain hidden from new workflow submissions.</p>
        </div>
      </div>

      <form className="catalogue-filter-bar" method="get">
        <label className="catalogue-search-control">
          <Search size={18} color="#777c90" />
          <input name="q" defaultValue={filters.q || ""} placeholder="Search services by name, provider or capability..." aria-label="Search services" />
        </label>
        <label className="catalogue-select-control">
          <SlidersHorizontal size={15} color="#777c90" />
          <select name="category" defaultValue={filters.category || ""} aria-label="Filter by category">
            <option value="">All categories</option>
            {categories.map((category) => <option value={category} key={category}>{category}</option>)}
          </select>
        </label>
        <label className="catalogue-select-control">
          <Building2 size={15} color="#777c90" />
          <select name="provider" defaultValue={filters.provider || ""} aria-label="Filter by provider">
            <option value="">All providers</option>
            {providers.map((provider) => <option value={provider} key={provider}>{provider}</option>)}
          </select>
        </label>
        <button type="submit" style={{ whiteSpace: "nowrap" }}>Apply filters</button>
        {hasFilters && <Link href="/catalogue" style={{ alignSelf: "center", padding: "8px 5px", color: "#5d3ddd", fontSize: 11, fontWeight: 800 }}>Clear</Link>}
      </form>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", margin: "25px 2px 13px" }}>
        <div><span style={{ color: "#6b49e7", fontSize: 9, fontWeight: 900, letterSpacing: "0.12em", textTransform: "uppercase" }}>Trusted services</span><h2 style={{ margin: "5px 0 0", fontSize: 20 }}>Available in the catalogue</h2></div>
        <span style={{ color: "#777c90", fontSize: 11 }}>{visibleServices.length} of {services.length} services</span>
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

      <div className="catalogue-service-grid">
        {visibleServices.map((service) => {
          const lifecycleStatus = getLifecycleStatus(service);
          const isDeprecated = lifecycleStatus === "deprecated";
          const presentation = getServicePresentation(service);

          return (
            <div
              className="card catalogue-service-card"
              key={service.id}
              style={{
                display: "flex",
                minHeight: 400,
                padding: 22,
                flexDirection: "column",
                border: isDeprecated ? "1px solid #fde68a" : undefined,
                background: isDeprecated ? "#fffdf7" : undefined,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                <span className="badge">{service.trust_badge || "Trusted"}</span>
                <span style={{ color: "#777c90", fontSize: 11, fontWeight: 700 }}>
                  v{service.version || "1.0.0"}
                </span>
              </div>

              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 12,
                  alignItems: "flex-start",
                  marginTop: 16,
                }}
              >
                <div>
                  <h2 style={{ margin: 0, fontSize: 20, letterSpacing: "-0.02em" }}>{presentation.displayName}</h2>
                  {presentation.displayName !== service.name && (
                    <div className="catalogue-technical-name">{service.name}</div>
                  )}
                </div>
                <span style={lifecycleBadgeStyle(lifecycleStatus)}>{lifecycleStatus}</span>
              </div>

              <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 9, color: "#646b82", fontSize: 11 }}>
                <span><strong style={{ color: "#343955" }}>Provider:</strong> {service.provider || "Unknown"}</span>
                <span><strong style={{ color: "#343955" }}>Category:</strong> {service.category || "Uncategorised"}</span>
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

              <p className="catalogue-service-purpose">
                {presentation.purpose}
              </p>

              <div className="catalogue-workflow-stage">{presentation.stage}</div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 4, padding: 13, borderRadius: 12, background: "#f9f8fd", fontSize: 11 }}>
                <div><span style={{ display: "block", color: "#85899a", fontSize: 9 }}>INPUT</span><strong style={{ wordBreak: "break-word" }}>{service.input_type || "Not specified"}</strong></div>
                <div><span style={{ display: "block", color: "#85899a", fontSize: 9 }}>OUTPUT</span><strong style={{ wordBreak: "break-word" }}>{service.output_type || "Not specified"}</strong></div>
              </div>

              <div style={{ display: "flex", gap: 10, marginTop: "auto", paddingTop: 20 }}>
                <Link
                  href={`/catalogue/${service.id}`}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: 7,
                    background: "linear-gradient(135deg, #5b2cf2, #4320ca)",
                    color: "white",
                    padding: "10px 14px",
                    borderRadius: 10,
                    fontSize: 11,
                    fontWeight: 800,
                  }}
                >
                  View details <ArrowRight size={14} />
                </Link>
                <Link
                  href={`/builder?serviceId=${encodeURIComponent(service.id)}`}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    border: "1px solid #d8d2f2",
                    background: "#f8f6ff",
                    color: "#5637ce",
                    padding: "10px 14px",
                    borderRadius: 10,
                    fontSize: 11,
                    fontWeight: 800,
                  }}
                >
                  Add to solution
                </Link>
              </div>
            </div>
          );
        })}
      </div>

      {visibleServices.length === 0 && (
        <div className="card" style={{ padding: 24, marginTop: 28 }}>
          <h2>{services.length === 0 ? "No catalogue services available" : "No matching services"}</h2>
          <p style={{ color: "#526173" }}>
            {services.length === 0
              ? "No active or deprecated services are currently visible. Archived services can be managed from Admin Governance."
              : "Try adjusting your search, category, or provider filters."}
          </p>
        </div>
      )}
    </div>
  );
}

function StatusMetric({ label, value, color, background }: { label: string; value: number; color: string; background: string }) {
  return <div style={{ padding: "10px 8px", borderRadius: 10, background, textAlign: "center" }}><strong style={{ display: "block", color, fontSize: 19 }}>{value}</strong><span style={{ color, fontSize: 8, fontWeight: 800, textTransform: "uppercase" }}>{label}</span></div>;
}
