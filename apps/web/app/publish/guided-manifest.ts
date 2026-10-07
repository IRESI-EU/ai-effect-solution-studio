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
  internalPort: string;
  healthPath: string;
  operationName: string;
  interfaceType: InterfaceChoice;
  contractUri: string;
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
  internalPort: "8080",
  healthPath: "/health",
  operationName: "",
  interfaceType: "control",
  contractUri: "ai-effect.service.json",
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
  if (form.interfaceType === "grpc") {
    interfaceBlock.grpc = {
      proto_uri: form.contractUri.trim(),
      operation_name: form.operationName.trim(),
      input_message_name: form.grpcInputMessage.trim(),
      output_message_name: form.grpcOutputMessage.trim(),
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
    internalPort: textValue(runtime.internal_port) || "8080",
    healthPath: textValue(runtime.health_path) || "/health",
    operationName: textValue(interfaceBlock.operation_name) || textValue(grpc.operation_name),
    interfaceType,
    contractUri: textValue(grpc.proto_uri) || textValue(interfaceBlock.contract_uri),
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
