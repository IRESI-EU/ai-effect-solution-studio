// Plain-language names and descriptions for catalogue services, shared by the
// catalogue, service detail page and Builder. Keyed by operation name; services a
// provider describes themselves (interface_contract.design) take precedence.
// Keep in step with apps/api/app/design_ai/catalogue.py (CURATED).

export type ServiceText = {
  title: string;
  purpose: string;
  stage: string;
  needs: string;
  produces: string;
};

type ServiceLike = {
  name: string;
  description?: string | null;
  operation_name?: string | null;
  interface_contract?: Record<string, unknown> | null;
};

const KNOWN: Record<string, ServiceText> = {
  BuildRunConfig: {
    title: "District-heating configuration assistant",
    purpose: "Turns a plain-language district-heating request into a structured run configuration, using a local language model.",
    stage: "First step of a district-heating network design workflow, before topology generation.",
    needs: "A request describing the supply and load points and any routing preferences.",
    produces: "A structured run configuration for the topology generator.",
  },
  GenerateTopology: {
    title: "District-heating topology generator",
    purpose: "Generates candidate district-heating network topologies from a run configuration.",
    stage: "After the configuration assistant, before the topologies are drawn.",
    needs: "A structured topology configuration.",
    produces: "Candidate network topologies.",
  },
  RenderTopologies: {
    title: "Topology drawings",
    purpose: "Draws generated network topologies as SVG images for review and comparison.",
    stage: "Last step of a district-heating workflow.",
    needs: "Candidate topologies from the topology generator.",
    produces: "A set of SVG network drawings.",
  },
  ConfigureAndSynthesize: {
    title: "Synthetic grid scenario",
    purpose: "Creates a reproducible synthetic electricity grid scenario for benchmarking.",
    stage: "First step of a grid benchmarking workflow, when real grid data is not available.",
    needs: "Scenario settings such as seed and loading level (optional).",
    produces: "A synthetic grid scenario for the benchmark runner.",
  },
  RunBenchmark: {
    title: "Grid control benchmark",
    purpose: "Runs a reproducible benchmark of AI and control approaches on a prepared grid scenario and reports KPIs.",
    stage: "After a synthetic grid scenario has been prepared.",
    needs: "A prepared grid scenario.",
    produces: "Benchmark KPIs and result files.",
  },
  ProvideData: {
    title: "German grid data provider",
    purpose: "Prepares German grid and time-series data for generating load and production profiles.",
    stage: "First step of the German time-series workflow.",
    needs: "Nothing; it starts the workflow.",
    produces: "Grid and time-series data for the chronics generator.",
  },
  GenerateChronics: {
    title: "VILLAS time-series generator",
    purpose: "Generates electricity load and production time series (chronics) with the VILLASnode simulator.",
    stage: "After the German grid data has been provided.",
    needs: "Grid and time-series data from the data provider.",
    produces: "Load and production time series as CSV files.",
  },
  FormatOutput: {
    title: "Time-series output check",
    purpose: "Checks generated time-series CSV files and produces a validation summary.",
    stage: "Last step of the German time-series workflow.",
    needs: "Time-series files from the VILLAS generator.",
    produces: "A validation summary of the generated files.",
  },
  ExecuteQuery: {
    title: "Energy data loader",
    purpose: "Loads energy data from a CSV file or a database query as the starting dataset.",
    stage: "First step of the Portuguese synthetic-data workflow.",
    needs: "A file path or SQL query (settings).",
    produces: "A dataset for feature engineering.",
  },
  ApplyFunction: {
    title: "Feature engineering",
    purpose: "Applies feature-engineering functions from a knowledge store to prepare data for model training.",
    stage: "After loading data, before training a model.",
    needs: "A dataset from the data loader.",
    produces: "Prepared features for model training.",
  },
  TrainModel: {
    title: "DGAN model trainer",
    purpose: "Trains a DoppelGANger (DGAN) generative model on prepared time-series data.",
    stage: "After feature engineering, before generating synthetic data.",
    needs: "Prepared time-series features.",
    produces: "A trained generative model.",
  },
  GenerateData: {
    title: "Synthetic data generator",
    purpose: "Generates synthetic data records, from a trained model or as simulated energy readings.",
    stage: "After model training or configuration, before analysis or reporting.",
    needs: "A trained model or a run configuration.",
    produces: "Synthetic data records.",
  },
  GetConfiguration: {
    title: "Pipeline configuration",
    purpose: "Provides the run configuration, such as how many records to generate, for an energy-data pipeline.",
    stage: "First step of the energy analysis pipeline.",
    needs: "Nothing; it starts the workflow.",
    produces: "A run configuration for the data generator.",
  },
  AnalyzeData: {
    title: "Energy efficiency analyser",
    purpose: "Analyses household energy readings: flags unusual consumption (anomalies) and scores efficiency.",
    stage: "After data generation, before writing a report.",
    needs: "Household energy readings.",
    produces: "Analysis results with anomalies and efficiency scores.",
  },
  GenerateReport: {
    title: "Energy analysis report",
    purpose: "Writes a readable report with a summary, per-household analysis and recommendations.",
    stage: "Last step of the energy analysis pipeline.",
    needs: "Analysis results.",
    produces: "A report for review and sharing.",
  },
};

function humanise(value: string) {
  const last = value.split("/").at(-1)?.trim() || value;
  return last
    .replace(/[_-]+/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/\s+\d+$/, "")
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .trim();
}

function isBoilerplate(description?: string | null) {
  const text = (description || "").trim().toLowerCase();
  return !text || text.startsWith("imported from") || text.startsWith("compatibility alias");
}

export function serviceText(service: ServiceLike): ServiceText {
  const design = (service.interface_contract?.design || {}) as Partial<Record<"title" | "purpose" | "use_when", string>>;
  const known = KNOWN[service.operation_name || ""];
  const purpose =
    design.purpose ||
    known?.purpose ||
    (isBoilerplate(service.description) ? "A service published by an AI-EFFECT node." : (service.description as string));
  return {
    title: design.title || known?.title || humanise(service.name),
    purpose,
    stage: design.use_when || known?.stage || "Place it in the Builder where its input matches the previous step's output.",
    needs: known?.needs || "The output of a compatible previous step.",
    produces: known?.produces || "A result for the next step or for review.",
  };
}

// Short labels for what flows in and out of a service, shown on the Builder's
// connection points and links. Keyed by operation name.
const PORTS: Record<string, { input?: string; output: string }> = {
  BuildRunConfig: { input: "request", output: "run configuration" },
  GenerateTopology: { input: "run configuration", output: "topologies" },
  RenderTopologies: { input: "topologies", output: "drawings" },
  ConfigureAndSynthesize: { input: "scenario settings", output: "grid scenario" },
  RunBenchmark: { input: "grid scenario", output: "KPIs" },
  ProvideData: { output: "grid data" },
  GenerateChronics: { input: "grid data", output: "time series" },
  FormatOutput: { input: "time series", output: "validation summary" },
  ExecuteQuery: { input: "data source", output: "dataset" },
  ApplyFunction: { input: "dataset", output: "features" },
  TrainModel: { input: "features", output: "trained model" },
  GenerateData: { input: "model or config", output: "synthetic records" },
  GetConfiguration: { output: "configuration" },
  AnalyzeData: { input: "energy readings", output: "analysis" },
  GenerateReport: { input: "analysis", output: "report" },
};

export const WORKFLOW_START = "Workflow Start";
export const WORKFLOW_OUTPUT = "Workflow Output";

type TypedService = ServiceLike & { input_type: string; output_type: string };

function typeLabel(type: string) {
  return humanise(type.replace(/\s+(Input|Request|Response)$/i, "")).toLowerCase();
}

/** Plain labels for a service's input and output, or null for the workflow's own start/end. */
export function servicePorts(service: TypedService): { input: string | null; output: string } {
  const known = PORTS[service.operation_name || ""];
  const input = service.input_type === WORKFLOW_START ? known?.input ?? null : known?.input || typeLabel(service.input_type);
  const output = known?.output || (service.output_type === WORKFLOW_OUTPUT ? "results" : typeLabel(service.output_type));
  return { input, output };
}

export type ServiceStage = "start" | "middle" | "finish" | "other";

/**
 * Where a service fits in a workflow, used to group the Builder's service list.
 * "other" means nothing in the catalogue can feed it or use its result yet.
 */
export function serviceStage(service: TypedService, catalogue: TypedService[]): ServiceStage {
  const starts = service.input_type === WORKFLOW_START;
  const ends = service.output_type === WORKFLOW_OUTPUT;
  const fed = starts || catalogue.some((other) => other !== service && other.output_type === service.input_type);
  const used = ends || catalogue.some((other) => other !== service && other.input_type === service.output_type);
  if (!fed || !used) return "other";
  if (starts) return "start";
  if (ends) return "finish";
  return "middle";
}

export type ServiceIcon =
  | "config" | "topology" | "drawing" | "grid" | "benchmark" | "data" | "timeseries" | "check"
  | "features" | "model" | "generate" | "analysis" | "report" | "service";

const ICONS: Record<string, ServiceIcon> = {
  BuildRunConfig: "config", GenerateTopology: "topology", RenderTopologies: "drawing",
  ConfigureAndSynthesize: "grid", RunBenchmark: "benchmark", ProvideData: "data",
  GenerateChronics: "timeseries", FormatOutput: "check", ExecuteQuery: "data",
  ApplyFunction: "features", TrainModel: "model", GenerateData: "generate",
  GetConfiguration: "config", AnalyzeData: "analysis", GenerateReport: "report",
};

export function serviceIcon(service: ServiceLike): ServiceIcon {
  return ICONS[service.operation_name || ""] || "service";
}
