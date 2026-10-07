import assert from "node:assert/strict";
import test from "node:test";
import { buildGuidedManifest, emptyGuidedForm, formFromExample } from "./guided-manifest";

test("guided REST details compile to the current importer schema", () => {
  const manifest = buildGuidedManifest({
    ...emptyGuidedForm,
    serviceId: "svc-workshop-forecast",
    name: "Workshop Forecast",
    provider: "German Node",
    category: "Forecasting",
    description: "Produces a forecast.",
    inputType: "Weather DataReference",
    outputType: "Forecast DataReference",
    image: "registry.example/forecast:1.0.0",
    containerName: "forecast-service",
    operationName: "Forecast",
    interfaceType: "http",
    contractUri: "openapi.json",
    httpMethod: "post",
    httpPath: "/forecast",
  });

  assert.deepEqual(manifest.interface, {
    type: "http",
    operation_name: "Forecast",
    input_type: "Weather DataReference",
    output_type: "Forecast DataReference",
    contract_uri: "openapi.json",
    http: {
      method: "POST",
      path: "/forecast",
      input_content_type: "application/json",
      output_content_type: "application/json",
    },
  });
  assert.deepEqual(manifest.orchestration, { mode: "sidecar" });
});

test("gRPC details use the nested contract required by the importer", () => {
  const manifest = buildGuidedManifest({
    ...emptyGuidedForm,
    serviceId: "svc-grpc-test",
    name: "gRPC test",
    provider: "Dutch Node",
    category: "Synthesis",
    inputType: "Config DataReference",
    outputType: "Grid DataReference",
    image: "registry.example/grpc:sha-123",
    containerName: "grpc-test",
    operationName: "Synthesize",
    interfaceType: "grpc",
    contractUri: "contracts/synth.proto",
    grpcInputMessage: "SynthesisRequest",
    grpcOutputMessage: "SynthesisResponse",
  });
  const interfaceBlock = manifest.interface as Record<string, unknown>;

  assert.deepEqual(interfaceBlock.grpc, {
    proto_uri: "contracts/synth.proto",
    operation_name: "Synthesize",
    input_message_name: "SynthesisRequest",
    output_message_name: "SynthesisResponse",
  });
  assert.deepEqual(manifest.orchestration, { mode: "native" });
});

test("using an example as a starting point clears its identity", () => {
  const cloned = formFromExample({
    service: { id: "example-id", name: "Example", provider: "Danish Node", category: "Configuration" },
    runtime: { container_name: "config", image: "example/config:1" },
    interface: { type: "control", operation_name: "Build", input_type: "Request", output_type: "Config" },
  });

  assert.equal(cloned.serviceId, "");
  assert.equal(cloned.name, "");
  assert.equal(cloned.provider, "Danish Node");
  assert.equal(cloned.operationName, "Build");
});
