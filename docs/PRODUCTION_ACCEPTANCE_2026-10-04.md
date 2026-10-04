# Production acceptance — 2026-10-04

This record covers the private production candidate on `evpa-uat` before the
public Traefik route is moved from the legacy portal to Solution Studio.

## Architecture exercised

Browser traffic reaches Traefik, then the Solution Studio web container. The
web container proxies `/api` to the private API container. The API submits
compiled WP3 payloads to the loopback/private orchestrator, whose workers call
country services on the external `ai-effect-services` Docker network. Country
services publish no host ports.

## Pinned sources

- Solution Studio: `e8b817c` plus deployment commits through this record.
- German, Portuguese, Danish WP3 source: `e8914565e966a2d78879c314f980574769d31b87`.
- Dutch WP3 source: `ba598b2459f9986dac4e37dcc5d7d3298f25dc3a`.
- German VILLAS Node: `f2fbc82b5f7457c6c276260fd977e7a991d02f5e`.
- Dutch Git dependencies: see `deploy/country-nodes/dutch-dependency-pins.patch`.

## End-to-end results

Each test used the staged Solution Studio endpoint, including catalogue
approval, runtime preflight, workflow compilation, orchestrator submission,
worker execution, and output-reference verification.

| Use case | Workflow | Result | Completed tasks |
| --- | --- | --- | --- |
| Germany | `wf-1dbaa6bdf5b8` | PASS | ProvideData, GenerateChronics, FormatOutput |
| Portugal | `wf-ff7e0346d90e` | PASS | ExecuteQuery, ApplyFunction, TrainModel, GenerateData |
| Denmark | `wf-075a4fcef6fe` | PASS | BuildRunConfig, GenerateTopology, RenderTopologies |
| Netherlands | `wf-ba5ff8c723fc` | PASS | ConfigureAndSynthesize, RunBenchmark |

All twelve tasks completed without an error and returned one output reference.

## Security and operations checks

- Country services have Docker-internal ports only; none are published on the
  host.
- Solution Studio staging listens only on `127.0.0.1:13000`.
- The orchestrator listens only on `127.0.0.1:18000`; Redis has no host port.
- Production secrets are server-only and mode `0600`.
- The Portuguese source copy excludes its development `.env`, private test
  certificate, cached datasets, executable utilities, and cached models.
- PostgreSQL backups run nightly with fourteen-day retention.
- Server disk after all builds: 97 GiB available (48% used).
- The unrelated public `0.0.0.0:8080` listener belongs to the existing
  `powerpal-traefik` container, not an AI-EFFECT country node.

## Re-run

From `/home/renew/ai-effect-country-nodes/overlays` on the server:

```bash
python3 import_release_candidate.py
python3 validate_release_candidate.py
```

The importer is idempotent for these deterministic service IDs. The validator
creates fresh workflows and fails if preflight, workflow status, task status,
or output-reference checks fail.

## Public cutover

The public cutover completed on 2026-10-04 using Solution Studio commit
`4bbae05`.

- `https://portal.renewenergy.io/` and `https://platform.ai-effect.eu/` return
  HTTP 200 with valid TLS and serve the new Solution Studio frontend.
- `/api/health` and the read-only service catalogue are public. Management UI
  and API paths require HTTP Basic Authentication; unauthenticated checks
  return HTTP 401 and authenticated checks return HTTP 200.
- The production catalogue contains sixteen services, including the twelve
  accepted services from the German, Portuguese, Danish, and Dutch nodes.
- The legacy `ai-effect-nginx` frontend is stopped. Its backend and database
  remain in place as a short-term rollback option.
- The new web, API, and PostgreSQL containers were healthy after cutover, and
  Traefik reported no new routing errors.
- Independent HTTPS requests from the deployment workstation returned HTTP 200
  for both public homepages and the public health endpoint.
