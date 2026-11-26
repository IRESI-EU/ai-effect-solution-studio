export type InterfaceChoice = "control" | "http" | "grpc" | "container_job" | "legacy_sidecar";

export type GuidedServiceForm = {
  name: string;
  provider: string;
  category: string;
  version: string;
  description: string;
  inputType: string;
  outputType: string;
  serviceId: string;
  image: string;
  dockerfile: string;
  containerName: string;
  internalHost: string;
  internalPort: string;
  healthPath: string;
  operationName: string;
  inputMessageName: string;
  outputMessageName: string;
  interfaceType: InterfaceChoice;
  contractUri: string;
  protoUri: string;
  grpcInputMessage: string;
  grpcOutputMessage: string;
  httpMethod: string;
  httpPath: string;
  jobCommand: string;
  legacyAdapter: string;
  sourceReference: string;
  sourceRevision: string;
};

export const emptyGuidedForm: GuidedServiceForm = {
  name: "",
  provider: "",
  category: "",
  version: "0.1.0",
  description: "",
  inputType: "",
  outputType: "",
  serviceId: "",
  image: "",
  dockerfile: "",
  containerName: "",
  internalHost: "",
  internalPort: "8080",
  healthPath: "/health",
  operationName: "",
  inputMessageName: "",
  outputMessageName: "",
  interfaceType: "control",
  contractUri: "ai-effect.service.json",
  protoUri: "",
  grpcInputMessage: "",
  grpcOutputMessage: "",
  httpMethod: "POST",
  httpPath: "/run",
  jobCommand: "",
  legacyAdapter: "",
  sourceReference: "provider-supplied",
  sourceRevision: "",
};

export function buildGuidedManifest(form: GuidedServiceForm): Record<string, unknown> {
  const runtime: Record<string, unknown> = {
    type: "docker",
    container_name: form.containerName.trim(),
    internal_host: form.internalHost.trim() || form.containerName.trim(),
    internal_port: form.internalPort.trim() || "8080",
    health_path: form.healthPath.trim() || "/health",
  };
  if (form.image.trim()) runtime.image = form.image.trim();
  if (form.dockerfile.trim()) runtime.dockerfile = form.dockerfile.trim();

  const interfaceBlock: Record<string, unknown> = {
    type: form.interfaceType,
    operation_name: form.operationName.trim(),
    input_type: form.inputType.trim(),
    output_type: form.outputType.trim(),
  };

  if (form.contractUri.trim()) interfaceBlock.contract_uri = form.contractUri.trim();
  if (form.protoUri.trim()) interfaceBlock.proto_uri = form.protoUri.trim();
  if (form.inputMessageName.trim()) interfaceBlock.input_message_name = form.inputMessageName.trim();
  if (form.outputMessageName.trim()) interfaceBlock.output_message_name = form.outputMessageName.trim();
  if (form.interfaceType === "grpc") {
    interfaceBlock.grpc = {
      proto_uri: form.protoUri.trim() || form.contractUri.trim(),
      operation_name: form.operationName.trim(),
      input_message_name: form.grpcInputMessage.trim() || form.inputMessageName.trim(),
      output_message_name: form.grpcOutputMessage.trim() || form.outputMessageName.trim(),
    };
  } else if (form.interfaceType === "http") {
    interfaceBlock.http = {
      method: form.httpMethod.trim().toUpperCase() || "POST",
      path: form.httpPath.trim(),
      input_content_type: "application/json",
      output_content_type: "application/json",
    };
  } else if (form.interfaceType === "container_job") {
    interfaceBlock.container_job = { command: form.jobCommand.trim() };
  } else if (form.interfaceType === "legacy_sidecar") {
    interfaceBlock.legacy_sidecar = { adapter_type: form.legacyAdapter.trim() };
  }

  return {
    schema_version: "1.0",
    service: {
      id: form.serviceId.trim(),
      name: form.name.trim(),
      provider: form.provider.trim(),
      category: form.category.trim(),
      version: form.version.trim() || "0.1.0",
      description: form.description.trim(),
      trust_badge: "pending_review",
    },
    runtime,
    interface: interfaceBlock,
    orchestration: {
      mode: ["http", "container_job", "legacy_sidecar"].includes(form.interfaceType)
        ? "sidecar"
        : "native",
      ...(form.interfaceType === "legacy_sidecar" && form.legacyAdapter.trim()
        ? { adapter: form.legacyAdapter.trim() }
        : {}),
    },
  };
}

export function formFromExample(manifest: Record<string, unknown>): GuidedServiceForm {
  const service = objectValue(manifest.service);
  const runtime = objectValue(manifest.runtime);
  const interfaceBlock = objectValue(manifest.interface);
  const interfaceType = supportedInterface(interfaceBlock.type);
  const grpc = objectValue(interfaceBlock.grpc);
  const http = objectValue(interfaceBlock.http);
  const job = objectValue(interfaceBlock.container_job);
  const legacy = objectValue(interfaceBlock.legacy_sidecar);

  return {
    ...emptyGuidedForm,
    name: "",
    serviceId: "",
    provider: textValue(service.provider),
    category: textValue(service.category),
    version: textValue(service.version) || "0.1.0",
    description: textValue(service.description),
    inputType: textValue(interfaceBlock.input_type),
    outputType: textValue(interfaceBlock.output_type),
    image: textValue(runtime.image),
    dockerfile: textValue(runtime.dockerfile),
    containerName: textValue(runtime.container_name),
    internalHost: textValue(runtime.internal_host) || textValue(runtime.container_name),
    internalPort: textValue(runtime.internal_port) || "8080",
    healthPath: textValue(runtime.health_path) || "/health",
    operationName: textValue(interfaceBlock.operation_name) || textValue(grpc.operation_name),
    inputMessageName: textValue(interfaceBlock.input_message_name),
    outputMessageName: textValue(interfaceBlock.output_message_name),
    interfaceType,
    contractUri: textValue(interfaceBlock.contract_uri),
    protoUri: textValue(interfaceBlock.proto_uri) || textValue(grpc.proto_uri),
    grpcInputMessage: textValue(grpc.input_message_name),
    grpcOutputMessage: textValue(grpc.output_message_name),
    httpMethod: textValue(http.method) || "POST",
    httpPath: textValue(http.path) || "/run",
    jobCommand: textValue(job.command),
    legacyAdapter: textValue(legacy.adapter_type),
  };
}

function objectValue(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function textValue(value: unknown): string {
  return value === null || value === undefined ? "" : String(value);
}

function supportedInterface(value: unknown): InterfaceChoice {
  return ["control", "http", "grpc", "container_job", "legacy_sidecar"].includes(String(value))
    ? (String(value) as InterfaceChoice)
    : "control";
}

/** Like formFromExample, but keeps the service's own name and ID (for the person's own manifest). */
export function formFromManifest(manifest: Record<string, unknown>): GuidedServiceForm {
  const service = objectValue(manifest.service);
  return { ...formFromExample(manifest), name: textValue(service.name), serviceId: textValue(service.id) };
}

/**
 * The manifest to submit: the original one (from Git or a file) with the form's values on top,
 * so fields the form does not know about are kept unchanged.
 */
export function mergeManifest(base: Record<string, unknown> | null, form: GuidedServiceForm): Record<string, unknown> {
  const built = buildGuidedManifest(form);
  return base ? deepMerge(base, built) : built;
}

function deepMerge(base: Record<string, unknown>, top: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = { ...base };
  for (const [key, value] of Object.entries(top)) {
    const current = out[key];
    out[key] =
      value && typeof value === "object" && !Array.isArray(value) && current && typeof current === "object" && !Array.isArray(current)
        ? deepMerge(current as Record<string, unknown>, value as Record<string, unknown>)
        : value;
  }
  return out;
}

export function slugify(text: string) {
  return text.toLowerCase().normalize("NFKD").replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60);
}

export type ProtoOperation = { name: string; input: string; output: string };

/** Reads the rpc lines of a .proto file: rpc Name (Request) returns (Response). */
export function parseProtoOperations(text: string): ProtoOperation[] {
  const withoutComments = text.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*$/gm, "");
  const found: ProtoOperation[] = [];
  const rpc = /rpc\s+(\w+)\s*\(\s*(?:stream\s+)?([\w.]+)\s*\)\s*returns\s*\(\s*(?:stream\s+)?([\w.]+)\s*\)/g;
  let match: RegExpExecArray | null;
  while ((match = rpc.exec(withoutComments))) found.push({ name: match[1], input: match[2], output: match[3] });
  return found;
}
