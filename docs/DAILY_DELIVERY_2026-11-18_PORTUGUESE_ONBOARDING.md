# Daily delivery — Portuguese-priority onboarding, 18 November 2026

## Target and result

**Target:** a provider can select an existing owned service, supply source-backed OpenAPI, select the actual operation, discover adjustable query settings and save a reviewed draft through normal Publish. The same implementation must accept other nodes' interface descriptions and feed the existing Builder/Design with AI configuration path after qualification.

**Implemented:** query, JSON and form input discovery; explicit source-operation selection in Publish; source locations and limitations; review drafts for every interface type; publication guarded by a qualified supported configuration connector. The shared parameter core, contracts, Builder, canonical saved-solution writer, compiler and provider adapter remain in use. No Portuguese service IDs, workflow templates or reviewer allowlists were added to the generic feature.

**Locally verified:** normal authenticated provider/designer API journeys and rendered form/component behavior. A source-based Portuguese training definition reaches per-instance manual controls and an explicitly applied chat proposal, then compiles via the existing path. That qualification and chat response are **synthetic offline fixtures**, not Portuguese algorithm or live-model acceptance. The separate Danish real HTTP/Redis/enumerator/renderer execution journey is retained in regression coverage.

**Production deployed:** no. The Windows retained demo, saved designs/results, production and old spending scopes were not changed. This is a development-branch feature, not a production demonstration invitation.

## What can be demonstrated

In the development version, use normal provider authentication and Publish's existing-service selector. Choose the service whose actual upstream operation is being reviewed; this is not a service-ID registration script.

1. Upload [portugal-source-openapi.json](parameter-onboarding/portugal-source-openapi.json), an **input-signature export** from the pinned integrated Portuguese source. It is not observed live OpenAPI and does not claim deployed-version equivalence.
2. Select the real `POST /train` or `GET /generate` operation from the supplied document. The Portal no longer requires guessing its operation ID from the Control method name.
3. Inspect discovered candidates, exact schema pointers and query/body locations. CSV upload, model reference, account identity, overwrite and response format remain separate from algorithm settings. Unsupported dataset-column free text stays unselectable until a supported provider description exists.
4. Select settings, review meanings/defaults/limits and record actual algorithm mapping. Save a versioned draft without claiming runtime tests that have not happened. A non-Control interface can save definitions too; it cannot publish execution settings without a supported configuration connector.
5. For a qualified connector, download the draft qualification contract, perform actual runtime checks and record evidence; normal administrator service approval and provider publication remain required. No upload, discovery or Save starts an algorithm.
6. Existing Builder controls and Design with AI resolve the published contract. Offline acceptance changes the second of two training instances from 15 to 20 epochs, explicitly applies/saves it to the same solution, and compiles `[10, 20]` with source-declared defaults for the other settings. It leaves the first instance unchanged. This is configuration-delivery evidence, not model execution evidence.

## Source-backed candidates

The defaults below are observations from a particular source revision. The provider must confirm that they match its actual supported runtime. They are not scientific recommendations or approved production settings.

| Operation | Adjustable candidate | Declared source default | Declared limits |
| --- | --- | --- | --- |
| TrainModel / POST /train | `sequence_len` | 100 | None in inspected signature |
| TrainModel / POST /train | `batch_size` | 1000 | None in inspected signature |
| TrainModel / POST /train | `epochs` | 10 | None in inspected signature |
| GenerateData / GET /generate | `number_of_examples` | 1 | None in inspected signature |

No former sandbox maximums of 2 epochs or 20 examples were promoted to provider facts. `index_col` needs a dataset-aware supported definition; `return_csv` changes output representation and is excluded from ordinary algorithm controls. Name classification is conservative assistance, not a substitute for provider review.

Source: [integrated Synthetic Data API at the supplied PR4 baseline](https://github.com/AI-EFFECT/ai-effect-wp3/blob/d533219426af9ea6defaf0bc78956741201a5109/use-cases/portugal-node-integrated/synthetic_data_generation/main.py). Its file bytes match the current isolated WP3 checkout. Source SHA-256 and function/line provenance are embedded in the export. The generic optional helper `deploy/parameter_onboarding/export_fastapi_inputs.py` reads literal Query/File signatures using AST and FastAPI schema generation; it does not import service code, execute routes or load an ML library. It fails on unsupported expressions/constraints. Response contracts and authentication semantics are not inferred.

## Generic behavior and regression boundary

OpenAPI discovery includes inherited path-level query declarations and explicit operation overrides, local references, selected JSON/form bodies and exact source locations. Ambiguous names across locations remain unselectable. Unsupported body representations remain visible limitations; they are not silently declared supported. Header/cookie/path parameters cannot become algorithm settings, and excluded values/defaults are not retained in candidates.

The same provider route is checked with Portuguese, Danish, Dutch and German ownership fixtures. The existing Danish JSON-envelope real-runtime journey and retained Portuguese parameter/chain behavior remain regression cases. These fixtures demonstrate a common implementation; they do not establish owner approval or live integration for all nodes. Native gRPC and other interfaces still require an actual verified configuration connector for execution.

## Real Portuguese execution blocker and next target

The retained sidecar's training request uses `username` and `max_epochs`, while the inspected integrated API declares `user_id` and `epochs`. Generation similarly sends `username`/`output_format`, while the integrated API declares `user_id`/`return_csv`. This mismatch means the current wrapper cannot be assumed to consume all reviewed settings correctly. The algorithm source/runtime dependencies and retained ML image are not available as a running service in this workspace; the source package also does not include the imported `dgan` module. Historical image/model evidence is preserved, not reused as proof of current availability.

**Next showcase target:** qualify a Portuguese runtime mapping against the real available API, then demonstrate two explicitly selected configurations with distinct linked outputs through normal onboarding/Builder/Design with AI. Implementation of a connector must be driven by actual upstream parameter declarations and data/model authority. It must not revive the closed registered-workflow experiment as the general architecture. Work on other node interfaces and generic input/I/O contracts continues while that runtime dependency is resolved.

Provider-dependent facts: actual deployed API/source/image, supported meanings/defaults/limits (including sequence-length/data constraints), authorised training data and model references, parameter names consumed by the real runtime, resource limits, normal/invalid test evidence and owner publication approval. No approval or external access is invented. Production deployment and new paid-provider acceptance remain separate concrete approval steps.

## Evidence and cadence

The sanitized [source onboarding checkpoint](verification/portuguese-source-onboarding-20261118.json) records inspected declarations and the offline manual/chat configuration journey, with limitations. Final focused run: **151 backend checks passed**, including new discovery/provider/manual-chat fixtures, shared parameter/binding tests, both real Danish edit modes and retained Portuguese behavior. Frontend production build and TypeScript passed. **20 rendered provider/chat component checks passed.** The source snapshot and its published reference were separately rechecked with 15 source/onboarding checks. The portable contract-validator provenance check against WP3 passed.

Reproduce the source export without executing ML:

```sh
python deploy/parameter_onboarding/export_fastapi_inputs.py \
  --source ../wp3/use-cases/portugal-node-integrated/synthetic_data_generation/main.py \
  --source-reference https://github.com/AI-EFFECT/ai-effect-wp3/blob/d533219426af9ea6defaf0bc78956741201a5109/use-cases/portugal-node-integrated/synthetic_data_generation/main.py \
  --path /train --path /generate \
  --output docs/parameter-onboarding/portugal-source-openapi.json
```

Run the focused backend suite with `PYTHONPATH=apps/api WP3_SOURCE_ROOT=/absolute/path/to/matching/wp3 pytest -q` against `test_openapi_parameter_discovery`, `test_parameter_onboarding`, `test_saved_solution_assistant`, `test_native_control_execution`, `test_instance_parameters`, `test_capability_bindings`, `test_parameter_compatibility`, `test_portuguese_parameters`, `test_portuguese_chain` and `test_registered_portuguese` under `apps/api/tests`. The source snapshot's published reference was separately rechecked after the broad run; the source bytes are unchanged from the supplied PR4 base. `SOURCE_PARAMETER_EVIDENCE_FILE` optionally writes the sanitized source/API checkpoint.

From `apps/web`, run `npm run build` and `node --test app/publish/parameter-review.test.cjs app/design-ai/page.test.cjs components/saved-solution-assistant.test.cjs components/discovery-recommendation.test.cjs`. No browser or PostgreSQL acceptance is claimed by the portable API/component suite.

A daily development checkpoint is scheduled around 08:00 Europe/Dublin from 19 November. Each run must inspect actual current work, pursue one concrete user-visible slice when the environment permits, and report demonstrated behavior, implementation/local/production status, evidence, blockers and the next target. It must not claim unattended progress when an environment or owner dependency prevents it. The automation inherits the thread environment when available; its creation does not verify future environment availability.
