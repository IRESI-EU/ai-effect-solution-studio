import Link from "next/link";
import { ArrowLeft, Plus } from "lucide-react";
import type { CSSProperties } from "react";
import { ServiceSettingsEditor } from "../../../components/service-settings-editor";
import { settingsDefinitionOf } from "../../../lib/service-settings";
import { serviceText } from "../../../lib/service-presentation";

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
  owner_node?: string | null;
  orchestration_mode?: string | null;
  adapter_type?: string | null;
  health_path?: string | null;
  contract_uri?: string | null;
};

type ServicePresentation = {
  title: string;
  purpose: string;
  value: string;
  stage: string;
  input: string;
  output: string;
  limitations: string[];
};

const PRESENTATIONS: Record<string, Omit<ServicePresentation, "title">> = {
  BuildRunConfig: {
    purpose: "Turn a plain-language district-heating request into a structured run configuration.",
    value: "Reduces manual setup before topology generation and keeps the requested terminals and routing preferences together.",
    stage: "Use this near the start of a Danish district-heating workflow, before topology generation.",
    input: "A request describing the required supply and load terminals and any routing preferences.",
    output: "A structured run configuration for the topology generator.",
    limitations: [
      "Configuration quality depends on the detail in the original request.",
      "Generated settings should be reviewed before they are used for operational decisions.",
    ],
  },
  GenerateTopology: {
    purpose: "Generate candidate district-heating network topologies from a structured run configuration.",
    value: "Creates comparable network candidates that can be rendered and reviewed before a benchmark run.",
    stage: "Place after run configuration and before topology rendering.",
    input: "A structured topology-generation configuration.",
    output: "Candidate topology data for rendering and downstream assessment.",
    limitations: [
      "Candidates reflect the provider model and constraints rather than a live network state.",
      "Engineering review remains necessary before real-world use.",
    ],
  },
  RenderTopologies: {
    purpose: "Render generated topology candidates into visual network drawings.",
    value: "Makes generated network alternatives easier to inspect and compare.",
    stage: "Place after topology generation, typically at the end of a Danish visualisation workflow.",
    input: "Candidate topology data produced by the topology generator.",
    output: "A drawing index and SVG network visualisations.",
    limitations: [
      "Drawings are decision-support artifacts, not construction or control documents.",
      "Visual output depends on the completeness of the upstream topology data.",
    ],
  },
  ConfigureAndSynthesize: {
    purpose: "Prepare a reproducible synthetic energy-system scenario for benchmark execution.",
    value: "Provides a consistent fallback dataset when live or historical measurements are unavailable.",
    stage: "Use at the start of a Dutch synthetic benchmark workflow.",
    input: "Scenario configuration and synthesis parameters.",
    output: "A configured synthetic dataset for the benchmark runner.",
    limitations: [
      "Synthetic data does not represent current field conditions.",
      "Results should not be presented as measured operational performance.",
    ],
  },
  RunBenchmark: {
    purpose: "Run a reproducible benchmark against prepared energy data.",
    value: "Produces evidence that helps compare AI approaches under a consistent test setup.",
    stage: "Place after dataset preparation in a Dutch benchmark workflow.",
    input: "Prepared benchmark data and a compatible run configuration.",
    output: "Benchmark metrics and result artifacts for review.",
    limitations: [
      "Benchmark results apply only to the supplied data and configuration.",
      "They do not by themselves establish production suitability.",
    ],
  },
  GetConfiguration: {
    purpose: "Retrieve the configuration required for an energy-data workflow.",
    value: "Makes workflow settings explicit and available to downstream services.",
    stage: "Use before services that require a shared workflow configuration.",
    input: "A compatible workflow request or configuration reference.",
    output: "Configuration data for downstream processing.",
    limitations: ["Availability and content depend on the provider-managed configuration source."],
  },
  GenerateData: {
    purpose: "Generate the input dataset required by the Portuguese analysis pipeline.",
    value: "Supplies a predictable, file-based starting point for demonstrating the analysis workflow.",
    stage: "Use before data analysis in the Portuguese file-based pipeline.",
    input: "Workflow parameters accepted by the provider service.",
    output: "A file-backed data reference for the analysis service.",
    limitations: [
      "Generated data is intended for demonstration and validation scenarios.",
      "File availability is verified again during deployment preparation.",
    ],
  },
  AnalyzeData: {
    purpose: "Analyse an upstream energy dataset and produce structured findings.",
    value: "Transforms a prepared dataset into analysis results that can feed reporting.",
    stage: "Place after data generation and before report generation.",
    input: "A compatible file-backed data reference from an upstream service.",
    output: "Structured analysis results for the report generator.",
    limitations: [
      "This service requires an upstream input file and should not start a workflow.",
      "Findings remain subject to the quality and scope of the supplied data.",
    ],
  },
  GenerateReport: {
    purpose: "Turn structured analysis results into a reviewable report artifact.",
    value: "Packages workflow findings into a format that can be inspected and shared.",
    stage: "Use after data analysis, typically at the end of the Portuguese pipeline.",
    input: "Structured results from the analysis service.",
    output: "A report data reference for inspection or download.",
    limitations: ["The report reflects upstream results and does not add independent verification."],
  },
};

function getPresentation(service: Service): ServicePresentation {
  const operation = service.operation_name || service.name.split("/").at(-1) || "";
  const presentation = PRESENTATIONS[operation];

  return {
    title: presentation ? humanise(operation) : humanise(service.name),
    purpose:
      presentation?.purpose ||
      service.description ||
      "A reusable AI-EFFECT service that can be added to a governed solution workflow.",
    value:
      presentation?.value ||
      "Combine this service with compatible building blocks and validate the complete solution before deployment.",
    stage:
      presentation?.stage ||
      "Use the Builder to place this service in a compatible workflow and validate its connections.",
    input: presentation?.input || service.input_type || "Input requirements are recorded in the technical contract.",
    output: presentation?.output || service.output_type || "Output details are recorded in the technical contract.",
    limitations:
      presentation?.limitations || [
        "Runtime availability and compatibility are checked when the solution is prepared for deployment.",
      ],
  };
}

async function getService(id: string): Promise<Service> {
  const apiBaseUrl = process.env.INTERNAL_API_URL || "http://api:8080";
  const res = await fetch(`${apiBaseUrl}/services/${id}`, { cache: "no-store" });

  if (!res.ok) throw new Error("Failed to load service");
  return res.json();
}

export default async function ServiceDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const service = await getService(id);
  const presentation = getPresentation(service);
  const text = serviceText(service);
  const interfaceType = service.interface_type || "control";
  const orchestrationMode = service.orchestration_mode || "native";
  const healthPath = service.health_path || "/health";

  const lifecycle = service.lifecycle_status || "active";
  const statusTone = lifecycle === "deprecated" ? "warning" : lifecycle === "archived" ? "" : "success";
  const technical: [string, string | null | undefined][] = [
    ["Operation", service.operation_name],
    ["Interface", formatValue(interfaceType)],
    ["Orchestration", formatValue(orchestrationMode)],
    ["Adapter", service.adapter_type || "none"],
    ["Input message", service.input_type],
    ["Output message", service.output_type],
    ["Container", service.container_name],
    ["Image", service.image],
    ["Internal address", service.internal_host ? `${service.internal_host}:${service.internal_port || ""}` : null],
    ["Health endpoint", healthPath],
    ["Contract", service.contract_uri],
    ["Proto", service.proto_uri],
    ["Repository", service.repository_url ? `${service.repository_url}${service.repository_branch ? ` (${service.repository_branch})` : ""}` : null],
  ];

  return (
    <div className="page service-page">
      <Link href="/catalogue" className="back-link"><ArrowLeft size={16} aria-hidden="true" />Catalogue</Link>

      <header className="page-header">
        <div className="page-header__text">
          <div className="service-page__meta">
            <span className="ae-service__node">{service.provider || "Unknown provider"}</span>
            <span className={`ae-badge ${statusTone ? `ae-badge--${statusTone}` : ""}`}>{formatValue(lifecycle)}</span>
          </div>
          <h1 className="page-header__title">{text.title}</h1>
          <p className="page-header__lead">{text.purpose}</p>
        </div>
        <div className="page-header__actions">
          <Link href={`/builder?serviceId=${encodeURIComponent(service.id)}`} className="ae-btn ae-btn--primary"><Plus size={16} aria-hidden="true" />Add to a solution</Link>
        </div>
      </header>

      <div className="service-page__layout">
        <div className="service-page__main">
          <section className="ae-card service-section">
            <h2 className="section__title">Where it fits</h2>
            <p>{text.stage}</p>
          </section>

          <section className="service-io">
            <div className="ae-card service-io__item">
              <span className="service-io__label">Needs</span>
              <p>{text.needs}</p>
            </div>
            <div className="ae-card service-io__item">
              <span className="service-io__label">Produces</span>
              <p>{text.produces}</p>
            </div>
          </section>

          <ServiceSettingsEditor serviceId={service.id} ownerNode={service.owner_node || null} initial={settingsDefinitionOf(service)} />

          <section className="ae-card service-section">
            <h2 className="section__title">Limitations</h2>
            <ul className="service-list">
              {presentation.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}
            </ul>
          </section>

          <details className="details">
            <summary>Technical details</summary>
            <div className="details__body">
              <dl className="kv">
                {technical.filter(([, value]) => value).map(([label, value]) => (
                  <div key={label} style={{ display: "contents" }}><dt>{label}</dt><dd className="ae-mono">{value}</dd></div>
                ))}
              </dl>
              {service.interface_contract && (
                <details className="details">
                  <summary>Raw interface contract</summary>
                  <pre className="code-block">{JSON.stringify(service.interface_contract, null, 2)}</pre>
                </details>
              )}
            </div>
          </details>
        </div>

        <aside className="service-page__aside">
          <div className="ae-card">
            <dl className="kv kv--stacked">
              <dt>Provided by</dt><dd>{service.provider || "Unknown provider"}</dd>
              <dt>Category</dt><dd>{service.category || "Uncategorised"}</dd>
              <dt>Version</dt><dd>{service.version || "1.0.0"}</dd>
              <dt>Review status</dt><dd>{formatValue(service.status || "pending review")}</dd>
            </dl>
          </div>
        </aside>
      </div>
    </div>
  );
}

function Info({ title, value }: { title: string; value: string }) {
  return (
    <div className="service-detail-fact">
      <span>{title}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ContractRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="service-contract-row">
      <strong>{label}</strong>
      <span>{value}</span>
    </div>
  );
}

function humanise(value: string) {
  return value
    .replaceAll("_", " ")
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .replace(/^\w/, (letter) => letter.toUpperCase());
}

function formatValue(value?: string | null) {
  if (!value) return "Not specified";
  return humanise(value);
}

const metadataBadgeStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  border: "1px solid #cbd5e1",
  borderRadius: 999,
  padding: "5px 9px",
  fontSize: 11,
  fontWeight: 800,
  letterSpacing: "0.03em",
  background: "#ffffff",
  color: "#334155",
};

function lifecycleBadgeStyle(status: string): CSSProperties {
  if (status === "deprecated") return { ...metadataBadgeStyle, background: "#fef3c7", color: "#92400e", borderColor: "#fde68a" };
  if (status === "archived") return { ...metadataBadgeStyle, background: "#f1f5f9", color: "#475569", borderColor: "#cbd5e1" };
  return { ...metadataBadgeStyle, background: "#dcfce7", color: "#166534", borderColor: "#bbf7d0" };
}

function interfaceBadgeStyle(value?: string | null): CSSProperties {
  const normalized = value || "control";
  if (normalized === "grpc") return { ...metadataBadgeStyle, background: "#eef2ff", color: "#3730a3", borderColor: "#c7d2fe" };
  if (normalized === "http") return { ...metadataBadgeStyle, background: "#ecfeff", color: "#0e7490", borderColor: "#a5f3fc" };
  if (normalized === "container_job") return { ...metadataBadgeStyle, background: "#f5f3ff", color: "#6d28d9", borderColor: "#ddd6fe" };
  if (normalized === "legacy_sidecar") return { ...metadataBadgeStyle, background: "#fff7ed", color: "#c2410c", borderColor: "#fed7aa" };
  return { ...metadataBadgeStyle, background: "#f0fdf4", color: "#047857", borderColor: "#bbf7d0" };
}

function orchestrationBadgeStyle(value?: string | null): CSSProperties {
  const normalized = value || "native";
  if (normalized === "sidecar") return { ...metadataBadgeStyle, background: "#fffbeb", color: "#92400e", borderColor: "#fde68a" };
  if (normalized === "external") return { ...metadataBadgeStyle, background: "#f8fafc", color: "#475569", borderColor: "#cbd5e1" };
  if (normalized === "manual_review") return { ...metadataBadgeStyle, background: "#fef2f2", color: "#b91c1c", borderColor: "#fecaca" };
  return { ...metadataBadgeStyle, background: "#eff6ff", color: "#1d4ed8", borderColor: "#bfdbfe" };
}
