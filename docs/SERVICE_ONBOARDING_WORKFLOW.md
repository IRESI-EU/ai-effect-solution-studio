# Production Service Onboarding Workflow

## Purpose

This workflow separates catalogue registration from production deployment. A
service is usable in Solution Studio only when both are complete:

```text
source -> reviewed container runtime -> production network
   \-> service manifest -> pending catalogue record -> admin approval
```

Importing a manifest never authorizes the portal to clone or execute arbitrary
repository code on the production server.

## Roles

| Role | Responsibility |
|---|---|
| Node Manager | Supplies source traceability, one manifest per service, runtime requirements, and provider evidence |
| IT / Node Operator | Reviews source, builds or pulls immutable images, supplies secrets and storage, and starts the runtime |
| Platform Admin | Verifies ownership, runtime reachability, health, operation contract, and evidence before approval |
| Solution Designer | Uses only approved and active services in Builder |

## Supported sources

### Available in the portal

- An exact `ai-effect.service.json` path in a public GitHub repository.
- Pasted manifest JSON with a repository or local-source reference.

The Git option fetches only the named JSON file. It does not clone the
repository or discover Dockerfiles, Compose files, blueprints, or services.

### Administrator-assisted

- WP3 `blueprint.json` plus `dockerinfo.json` packages.
- Private repositories accessed through an approved server-side deploy key or
  GitHub App.
- Local folders or ZIP packages transferred to a quarantined staging area.

Private credentials, environment files, certificates, datasets, and model
weights must never be pasted into a manifest.

## One manifest per runnable service

A use case is normally a workflow containing multiple services. For example, a
three-container pipeline requires three manifests and three catalogue records.
Each record identifies one operation endpoint that WP3 can call.

Every service must declare:

- immutable source reference (commit SHA or tag preferred);
- image and container identity;
- internal host, port, and health path;
- interface type and operation name;
- input and output semantic types;
- orchestration mode and adapter, when used;
- contract or `.proto` location;
- provider and node ownership.

## Runtime contract

The preferred native control interface is:

- `POST /control/execute`
- `GET /control/status/{task_id}` for asynchronous operations
- `GET /control/output/{task_id}` for asynchronous operations
- `GET /health`

Legacy HTTP, batch, or gRPC implementations require a reviewed adapter when
they do not implement this control interface directly. Outputs should use a
portable DataReference (`http`, `https`, `s3`, `artifact`, `inline`, or an
approved `grpc` endpoint). A `file` reference works only when production shares
the same mounted artifact volume with the portal.

## Lifecycle

```text
Source declared
-> Contract validated
-> Onboarding request submitted (pending_review)
-> Runtime deployed by operator
-> Runtime and security verified by admin
-> Approved and active
-> Available to Solution Designer
```

The provider evidence checklist is a declaration, not proof. Admin Governance
must independently verify it.

## Operator deployment checklist

1. Record repository URL, use-case path, and exact commit.
2. Review Dockerfiles, dependencies, licences, data access, and model origin.
3. Build or pull an immutable image and record its digest.
4. Scan the image and generate an SBOM when tooling is available.
5. Keep secrets in the server environment or secret manager.
6. Define private networks, volumes, resource limits, restart policy, and
   health check in a production Compose overlay.
7. Expose no public host port unless the architecture explicitly requires it.
8. Start the service and verify health from the Solution Studio API network.
9. Run an operation-level smoke test with representative input.
10. Confirm output DataReferences are accessible to downstream services and
    the portal.

## Admin approval checklist

Before approval, the administrator verifies:

- the requester belongs to the owning node;
- the source revision and image digest are immutable;
- required secrets are not stored in Git or the manifest;
- the configured container host and port are reachable in production;
- `/health` returns success;
- the declared operation and input/output contract match the runtime;
- storage and output references are accessible;
- an end-to-end acceptance workflow completes through Portal -> WP3 -> service
  -> artifact.

## Planned automation boundary

Future source discovery may inspect a repository and propose service records.
Future build automation must run in an isolated CI worker, publish signed images
to an approved registry, and require administrator promotion. Node users must
not be allowed to execute arbitrary Git code directly on the production host.
