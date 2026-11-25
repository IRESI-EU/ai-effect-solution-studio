import Link from "next/link";
import { ArrowRight, Plus, Search, SlidersHorizontal } from "lucide-react";
import { settingsDefinitionOf } from "../../lib/service-settings";
import { serviceText } from "../../lib/service-presentation";

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
  interface_contract?: Record<string, unknown> | null;
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
  const apiBaseUrl = process.env.INTERNAL_API_URL || "http://api:8080";

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


const STATUS: Record<string, { label: string; tone: string }> = {
  active: { label: "Active", tone: "success" },
  deprecated: { label: "Deprecated", tone: "warning" },
  archived: { label: "Archived", tone: "" },
};

function settingsSummary(service: Service) {
  const definition = settingsDefinitionOf(service);
  const count = definition ? Object.keys(definition.schema.properties).length : 0;
  if (!count) return "Fixed settings";
  return count === 1 ? "1 adjustable setting" : `${count} adjustable settings`;
}

export default async function CataloguePage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; category?: string; provider?: string }>;
}) {
  const services = await getServices();
  const filters = await searchParams;
  const query = (filters.q || "").trim().toLowerCase();

  const deprecatedCount = services.filter((service) => getLifecycleStatus(service) === "deprecated").length;
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
      <header className="page-header">
        <div className="page-header__text">
          <h1 className="page-header__title">Service catalogue</h1>
          <p className="page-header__lead">
            AI services published by AI-EFFECT nodes. Open a service to see what it needs and produces, or add it straight to a solution.
          </p>
        </div>
      </header>

      <form className="toolbar catalogue-toolbar" method="get" role="search">
        <label className="catalogue-search">
          <Search size={16} aria-hidden="true" />
          <input className="ae-input" name="q" defaultValue={filters.q || ""} placeholder="Search by name, node or capability" aria-label="Search services" />
        </label>
        <select className="ae-select catalogue-filter" name="category" defaultValue={filters.category || ""} aria-label="Category">
          <option value="">All categories</option>
          {categories.map((category) => <option value={category} key={category}>{category}</option>)}
        </select>
        <select className="ae-select catalogue-filter" name="provider" defaultValue={filters.provider || ""} aria-label="Node or provider">
          <option value="">All nodes and providers</option>
          {providers.map((provider) => <option value={provider} key={provider}>{provider}</option>)}
        </select>
        <button type="submit" className="ae-btn ae-btn--secondary"><SlidersHorizontal size={16} aria-hidden="true" />Apply</button>
        {hasFilters && <Link href="/catalogue" className="ae-btn ae-btn--ghost">Clear</Link>}
        <span className="catalogue-count muted">
          {visibleServices.length} of {services.length} services{deprecatedCount ? ` · ${deprecatedCount} deprecated` : ""}
        </span>
      </form>

      {visibleServices.length > 0 ? (
        <div className="grid-cards catalogue-grid">
          {visibleServices.map((service) => {
            const status = STATUS[getLifecycleStatus(service)] || STATUS.active;
            const text = serviceText(service);
            return (
              <article className="ae-card ae-card--interactive ae-service" key={service.id}>
                <div className="ae-service__top">
                  <span className="ae-service__node">{service.provider || "Unknown provider"}</span>
                  <span className={`ae-badge ${status.tone ? `ae-badge--${status.tone}` : ""}`}>{status.label}</span>
                </div>
                <h2 className="ae-service__title">
                  <Link href={`/catalogue/${service.id}`} className="catalogue-card-link">{text.title}</Link>
                </h2>
                <p className="ae-service__desc">{text.purpose}</p>
                <div className="ae-service__foot">
                  <span className="ae-service__io">{settingsSummary(service)}</span>
                  <span className="catalogue-card-actions">
                    <Link href={`/builder?serviceId=${encodeURIComponent(service.id)}`} className="ae-btn ae-btn--ghost ae-btn--sm" aria-label={`Add ${text.title} to a solution`}>
                      <Plus size={14} aria-hidden="true" />Add
                    </Link>
                    <Link href={`/catalogue/${service.id}`} className="ae-btn ae-btn--secondary ae-btn--sm">
                      Details<ArrowRight size={14} aria-hidden="true" />
                    </Link>
                  </span>
                </div>
              </article>
            );
          })}
        </div>
      ) : (
        <div className="ae-card empty-state">
          <h3>{services.length === 0 ? "No services yet" : "No services match your filters"}</h3>
          <p>{services.length === 0 ? "Services appear here once a node publishes them and an administrator approves them." : "Try a different search term, or clear the filters."}</p>
          {hasFilters && <Link href="/catalogue" className="ae-btn ae-btn--secondary">Clear filters</Link>}
        </div>
      )}
    </div>
  );
}
