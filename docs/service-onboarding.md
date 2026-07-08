# AI-EFFECT Service Onboarding

AI-EFFECT Solution Studio accepts Dockerized AI services that declare a machine-readable onboarding manifest.

The mandatory onboarding file is:

ai-effect.service.json

A .proto file is required only for services using the grpc interface type. Services using HTTP, container-job, or legacy sidecar patterns can be onboarded without a .proto file, provided they expose or are wrapped by the AI-EFFECT Control Interface.

## Required service contract

Every onboarded service must declare:

- service name, provider, category, version, and description
- Docker runtime information
- interface type
- operation name
- input and output semantic types
- health endpoint
- orchestration mode

## Supported interface types

| Type | Use case | Requires .proto? |
|---|---|---|
| control | Service directly implements /control/* endpoints | No |
| grpc | Service uses protobuf/gRPC interface metadata | Yes |
| http | REST/FastAPI/Flask service wrapped by adapter | No |
| container_job | Batch command/file-in-file-out service wrapped by adapter | No |
| legacy_sidecar | Existing service integrated through sidecar | No |

## AI-EFFECT Control Interface

The orchestrator-compatible control interface is:

POST /control/execute
GET /control/status/{id}
GET /control/output/{id}
GET /health

Services may implement these endpoints directly or expose them through a sidecar adapter.

## Example manifests

See:

- examples/service-manifest/ai-effect.control.example.json
- examples/service-manifest/ai-effect.grpc.example.json
- examples/service-manifest/ai-effect.http.example.json
- examples/service-manifest/ai-effect.container-job.example.json
- examples/service-manifest/ai-effect.sidecar.example.json

## Short-term orchestrator compatibility

The current WP3 orchestrator blueprint schema still expects proto_uri in each node. For non-gRPC services, Solution Studio maps contract_uri to proto_uri as a compatibility bridge.

Longer term, the orchestrator schema should evolve so proto_uri becomes optional and service nodes declare interface_type, contract_uri, orchestration_mode, and adapter_type.