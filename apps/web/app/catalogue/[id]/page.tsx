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
  const interfaceType = service.interface_type || "control";
  const orchestrationMode = service.orchestration_mode || "native";
  const healthPath = service.health_path || "/health";

  return (
    <div className="page service-detail-page">
      <Link href="/catalogue" className="service-detail-back">
        ← Back to catalogue
      </Link>

      <section className="card service-detail-hero">
        <div className="service-detail-badges">
          <span className="badge">{formatValue(service.trust_badge || "pending review")}</span>
          <span style={lifecycleBadgeStyle(service.lifecycle_status || "active")}>
            {formatValue(service.lifecycle_status || "active")}
          </span>
          <span style={interfaceBadgeStyle(interfaceType)}>{formatValue(interfaceType)}</span>
          <span style={orchestrationBadgeStyle(orchestrationMode)}>{formatValue(orchestrationMode)}</span>
        </div>
        <p className="service-detail-eyebrow">Service building block</p>
        <h1>{presentation.title}</h1>
        <p className="service-detail-technical-name">{service.name}</p>
        <p className="service-detail-purpose">{presentation.purpose}</p>

        <div className="service-detail-facts">
          <Info title="Provided by" value={service.provider || "Unknown provider"} />
          <Info title="Category" value={service.category || "Uncategorised"} />
          <Info title="Governance" value={formatValue(service.status || "pending review")} />
          <Info title="Version" value={`v${service.version || "1.0.0"}`} />
        </div>
      </section>

      <section className="service-detail-layout">
        <div className="service-detail-main">
          <section className="card service-detail-section">
            <p className="service-detail-eyebrow">Outcome</p>
            <h2>What this service contributes</h2>
            <p className="service-detail-lead">{presentation.value}</p>
          </section>

          <section className="service-detail-io-grid">
            <div className="card service-detail-io-card">
              <span className="service-detail-io-icon">IN</span>
              <div>
                <p className="service-detail-eyebrow">Required input</p>
                <h2>{service.input_type || "Workflow input"}</h2>
                <p>{presentation.input}</p>
              </div>
            </div>
            <div className="card service-detail-io-card">
              <span className="service-detail-io-icon service-detail-io-icon-output">OUT</span>
              <div>
                <p className="service-detail-eyebrow">Produced output</p>
                <h2>{service.output_type || "Workflow output"}</h2>
                <p>{presentation.output}</p>
              </div>
            </div>
          </section>

          <section className="card service-detail-section">
            <p className="service-detail-eyebrow">Workflow guidance</p>
            <h2>Where it fits</h2>
            <p className="service-detail-lead">{presentation.stage}</p>
          </section>

          <section className="card service-detail-section">
            <p className="service-detail-eyebrow">Responsible use</p>
            <h2>Limitations to consider</h2>
            <ul className="service-detail-limitations">
              {presentation.limitations.map((limitation) => (
                <li key={limitation}>{limitation}</li>
              ))}
            </ul>
          </section>
        </div>

        <aside className="card service-detail-action-card">
          <p className="service-detail-eyebrow">Build with this service</p>
          <h2>Add it to a solution</h2>
          <p>
            Open the visual Builder with this service selected. Compatibility, governance and runtime
            readiness are checked before deployment.
          </p>
          <Link href={`/builder?serviceId=${encodeURIComponent(service.id)}`} className="service-detail-primary-action">
            Add to solution <span aria-hidden="true">→</span>
          </Link>
          <div className="service-detail-readiness-note">
            <strong>Current catalogue state</strong>
            <span>{formatValue(service.lifecycle_status || "active")} · {formatValue(service.status || "pending review")}</span>
            <small>Runtime availability is checked when you prepare the complete solution.</small>
          </div>
        </aside>
      </section>

      <details className="card service-technical-panel">
        <summary>Technical integration details</summary>
        <div className="service-technical-grid">
          <div>
            <h2>Interface contract</h2>
            <ContractRow label="Interface type" value={formatValue(interfaceType)} />
            <ContractRow label="Orchestration" value={formatValue(orchestrationMode)} />
            <ContractRow label="Adapter" value={service.adapter_type || "none"} />
            <ContractRow label="Operation" value={service.operation_name || "Not specified"} />
            <ContractRow label="Contract URI" value={service.contract_uri || "Not declared"} />
            <ContractRow label="Proto URI" value={service.proto_uri || "Not declared"} />
            <ContractRow label="Health endpoint" value={healthPath} />
          </div>
          <div>
            <h2>Runtime &amp; source</h2>
            <ContractRow label="Container" value={service.container_name || "Not declared"} />
            <ContractRow label="Image" value={service.image || "Not declared"} />
            <ContractRow label="Internal host" value={service.internal_host || "Not declared"} />
            <ContractRow label="Internal port" value={service.internal_port || "Not declared"} />
            <ContractRow label="Repository" value={service.repository_url || "Not recorded"} />
            <ContractRow label="Branch" value={service.repository_branch || "Not recorded"} />
            <ContractRow label="Manifest" value={service.manifest_path || "Not recorded"} />
          </div>
        </div>

        {service.interface_contract && (
          <details className="service-raw-contract">
            <summary>View raw interface contract</summary>
            <pre>{JSON.stringify(service.interface_contract, null, 2)}</pre>
          </details>
        )}
      </details>
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
  textTransform: "uppercase",
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
