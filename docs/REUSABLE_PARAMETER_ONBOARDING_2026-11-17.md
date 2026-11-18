# Reusable provider parameter onboarding — implementation checkpoint

> Later checkpoint: [product alignment and delivery, 18 November](PRODUCT_ALIGNMENT_AND_DELIVERY_2026-11-18.md) corrects the draft qualification order and adds shared saved-solution chat. Evidence below describes the earlier pass.

Approved baseline: **AI_EFFECT_Product_Reset_and_Delivery_Plan.docx**, 17 November 2026, all eight pages read before development.

**Implemented:** the first missing product connection, normal provider onboarding to the existing versioned parameter contracts and Builder resolution. **Not complete:** real-node configuration consumption, general chat editing, independent browser acceptance or a production release.

## Environment and source findings

- New clean Portal clone and isolated branch `codex/reusable-provider-onboarding-20261117`, starting from supplied PR22 head `0c9930fc7591dfc54734803227753db379cd2ca4`. Portal default `main` is `70168fd14bfe4fe64229b16e1d75dbc1e419457d`.
- Separate read-only WP3 checkout at supplied PR4 head `d533219426af9ea6defaf0bc78956741201a5109`; default `main` is `e8914565e966a2d78879c314f980574769d31b87`. No WP3 files changed.
- This environment does not mount the Windows checkout or its Docker engine. Its dirty work, retained meeting demo, databases, designs, results and closed experimental scopes were not accessed or modified. They cannot be freshly inventoried here.
- Development uses only a new disposable database. No production migration, registration, approval, deployment, algorithm run or paid provider call occurred.
- The branch inherits the supplied draft code for inspection and reuse; it is **not** an instruction to install that stack or merge its PR chain. Release assembly from the verified serving baseline remains outstanding. This checkpoint introduces no new experimental service registry or execution exception.

### Fresh public production observations

Read-only HTTPS requests to `/`, `/api/health`, `/api/services` and `/api/openapi.json` returned 200. The catalogue contains 37 records. Existing contract CRUD/resolution routes are visible; `ExecutionParameterContract` is absent from the serving schema. This is API-surface evidence, not authenticated publishing/execution acceptance.

OpenAPI SHA-256: `4f453bf534f76c0dced0f2b33f540a5358121c3032822490bb80a366e4cd2e03`.
Observed frontend asset: `/_next/static/chunks/2q2m56wx_1j4h.js`.
Neither proves a serving source commit. Production image digests, frontend BUILD_ID, actual API/WP3 source, migration state and operator configuration could not be freshly inspected from this environment. Historical source identities in earlier evidence remain historical.

## Keep / change / gap

| Area | Keep | Implemented change or remaining gap |
|---|---|---|
| Catalogue and ownership | Existing publisher, node ownership, administrator service approval | Node-owned parameter discovery/review joins normal publishing and management. |
| Parameter core | `ParameterDefinition`, `ExecutionParameterContract`, shared validation and capability digest | Adds optional units. No duplicate value validator or per-service portal branch. |
| Contracts | Existing draft/active/deprecated lifecycle, immutable active versions | Reviewed definitions and provider attestations commit atomically; review is bound to definition and runtime metadata. |
| Builder and compiler | Existing instance controls, Save/reopen, per-instance pins and compiler | Activated definitions resolve through the existing endpoint; independent fixture settings persist and compile. Browser observation remains unverified. |
| Runtime and results | Existing configuration transport, capability negotiation and immutable submission support | The chosen real runtime still needs configuration-envelope delivery and consumed-value/result verification. |
| Chat | Existing server-side provider access and shared configuration validation | No chat changes in this slice. General catalogue editing and shared saved-solution integration remain incomplete. Existing special workflows are not the target architecture. |

## First service family and actual dependencies

**Selected implementation candidate:** Danish native Control topology family, `BuildRunConfig → GenerateTopology → RenderTopologies`. This is a source-backed integration selection, not a claim that its runtime is ready. Catalogue ownership is `denmark`; the named node maintainer and deployment/release owner are not established in this environment.

Source inspected in WP3 at `d533219426af9ea6defaf0bc78956741201a5109`:

- `use-cases/denmark-node/services/topology_generator/service.py`: `_generate_topology` reads `assistant_output['run_config']`; passes `allow_hx`, `allow_bypass` and `how_many` into the actual enumerator. It does **not** currently consume the published per-instance configuration envelope.
- `services/topology_generator/dh_network_generator.py`: the actual topology enumeration implementation.
- `services/config_assistant/service.py`: source defaults differ from the topology handler (`allow_bypass` in particular). Do not infer a provider-approved default or scientific limits from the old local pilot's bounds.
- `use-cases/denmark-node/README.md`: shared `/data` volume and file DataReference convention; infrastructure YAML and supplies/loads are required. Free-text configuration can involve Ollama; structured inputs should be assessed to avoid making chat/LLM availability a prerequisite for the first manual run.
- The topology validation operation is explicitly a placeholder. Do not present it as scientific validation.

`parameter-onboarding/denmark-candidates.schema.json` contains only the three observed **candidates**, with no fabricated defaults, bounds or confirmation. It is deliberately not an activatable approved runtime contract. The owner must confirm meanings/defaults/limits, the canonical operation identity/version, deployed source/image, configuration mapping, normal/invalid test evidence, data/volume access and output semantics. The runtime integration must then prove the configured values reach `enumerate_networks` and tie outputs to that run.

The Dutch generator/benchmark was also assessed. `docs/partner-review/dutch-parameters/contract-proposal.json` remains unconfirmed and describes local patch/runtime, latest-grid cache and immutable result-association gaps. It is not assumed ready. Portuguese work remains a regression source, with no new service-ID or reviewer restrictions carried into this feature.

## What a provider can now do

1. Register through the existing manifest or guided publisher. A manifest may include `interface.parameter_schema` or `interface.openapi`, with `interface.openapi_operation_id` when needed. Supported candidates are discovered during preview and persisted on confirmation; nothing is activated.
2. After registration, review settings directly below the confirmation. Existing services have a selector on the same Publish page. ZIP registrations use the same review component after selecting an imported service.
3. Supply or update a JSON Schema/OpenAPI JSON description. Discovery uses real source pointers, including local-reference targets, and records a source hash and fresh review revision. It makes no remote fetch or model call.
4. Select supported settings and confirm labels, meanings, types, optional units, defaults, required status, enumerations and numeric limits. Confirm the documentary algorithm mapping; executable transport remains the existing `configuration.parameters.<name>` envelope. The portal does not generate arbitrary field translations or adapters.
5. Record runtime evidence and attest actual consumption plus normal/invalid checks. Save a versioned **draft** through the existing registry. The provider identity, time, source, mappings and definition/runtime fingerprints are retained with an audit event.
6. After normal administrator service approval, inspect the saved definitions and publish the saved version. Existing Builder controls resolve that active definition. Changing either the reviewed draft or relevant runtime metadata blocks activation until a new review/version is supplied.

Discovery supports flat integer/number/boolean/enumerated-string fields, including documented `parameters` and `configuration.parameters` envelopes. Excluded secret/data/operator candidates retain no defaults or descriptions. Name classification is conservative assistance and does not establish that arbitrary documentation contains no sensitive information. Unsupported complex values, constraints and relationships are identified; they are not silently reduced to permissive primitives. External/cyclic schema references, prose and protobuf extraction need deliberate later support. Non-Control interfaces require a verified connector before this onboarding path can publish execution settings.

A registration with no parameter description remains usable through its existing fixed-service path. Active definitions are not modified by discovery or draft creation. New reviewed versions preserve existing operation inputs/outputs and bindings when an active contract exists. The current registry resolves one active operation contract per catalogue service; distinct callable operations continue to use distinct service records.

## Local verification and limits

- Focused authenticated integration checks cover provider registration, discovery, source pointer resolution, sensitive-field exclusion, governance denial, activation, independent designer Save/reopen, per-instance values, and compilation through the existing path.
- Further checks cover malformed/unconfirmed reviews, ownership/authentication, stale discovery revisions, changed definitions/runtime metadata, preservation of existing contracts and independent second-service metadata/units.
- Existing parameter and binding regression suites pass. TypeScript checking and the Next production build pass. No dependencies or lockfiles were changed by this feature.
- Final run: 72 focused backend checks and 3 existing guided-manifest checks passed. The backend was rechecked after installing the retained hash-verified dependency closure (`deploy/staging/build/requirements.lock`): FastAPI 0.142.2, Pydantic 2.13.5, SQLAlchemy 2.1.3, OpenAI SDK 2.54.0. Frontend: Next 16.3.8, React 19.3.0, TypeScript 7.0.2. Dependency consistency checking passed. These are development inputs, not observed production package versions.
- These API checks use the existing isolated SQLite test harness. They do not establish PostgreSQL row-locking, deployment migration or actual algorithm consumption.
- A browser walkthrough was attempted. Workspace Chromium could not start because process-singleton sockets are denied; the connected cloud browser could not reach the development server (`ERR_CONNECTION_REFUSED`). **No browser acceptance PASS is claimed.**
- No new results were generated. No normal user prompt-to-run acceptance or production deployment is claimed.

### Normal-user acceptance still to perform

Use a disposable deployment and separate ordinary provider, administrator and designer accounts. Onboard the supported runtime, inspect source-backed candidates, record genuine runtime evidence, save the draft, approve the service as administrator, publish as provider, and add it in Builder as the designer. Edit two instance configurations, Save/reopen, validate and explicitly run. Follow submitted values to actual consumption and the corresponding results. Repeat for a second independently onboarded runtime. This is the milestone gate; passing the current source tests does not replace it.

Immediate external dependencies: actual node/runtime owner confirmation and access to the retained/deployment environment for serving-version inventory and browser/PostgreSQL verification. Production deployment and new paid-provider acceptance remain separate approval decisions on concrete candidates.
