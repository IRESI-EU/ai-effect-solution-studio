# Qualified Dutch capture schema, version 1

This describes the **existing** `dutch-local-capture-v1` protocol and pinned
Dutch producer/consumer. It is not a universal JSON or pandapower contract.
Registry definitions are in [contracts.json](contracts.json); they refer here
through these exact versioned schema identities:

| Schema identity | Meaning |
|---|---|
| `urn:aieffect:nl:dutch-local-capture-v1:grid` | One immutable synthesis manifest, its protobuf JSON grid and native pandapower snapshot |
| `urn:aieffect:nl:dutch-local-capture-v1:benchmark` | One immutable benchmark manifest, original benchmark result and safe JSON export |

The protocol's executable schema/validation is
`apps/api/app/services/dutch_capture_contract.py`. The adapter is
`capture_algorithms.py`, a preserved copy of the earlier isolated capture
adapter, and `runtime.py` supplies typed instance parameters. The original node
algorithms and protobuf definitions are from AI-EFFECT/ai-effect-wp3 commit
`ba598b2459f9986dac4e37dcc5d7d3298f25dc3a`.

## Transport and required fields

Both contracts use a single DataReference:
`{"protocol":"file","format":"json","uri":"pilot-dutch://wf-<12 hex>/task_<8 hex>/<manifest SHA-256>"}`.
`file` denotes the existing local capture transport, **not an arbitrary host
path**. This URI is resolved only inside the purpose-specific adapter/authorized
artifact collector. Generic JSON/file services are not compatible.

Required manifest fields: `version`, `workflow_id`, `task_id`, `role`,
`method`, `request_sha256`, `status`, `files`, `upstream`, `provenance`.
Version is `dutch-local-capture-v1`; status must be `complete`. Each file entry
has `sha256` and `bytes`. Provenance identifies the base image, source revision,
adapter digest and capture-contract digest. The fixed role/task/method identities
are validated. The URI digest must match that exact manifest's bytes.

For synthesis, files are `configuration.json`, `grid.json` and
`network.pandapower.json`. Configuration contains the real node configuration
and observed `algorithm_consumed.seed`. The latter records the argument received
by `PowerGridGenerator.__init__`, after `generate_grid` returns.

`grid.json` is protobuf JSON with preserved snake_case field names for
`dutch.data_synthesizer.GetGridDataResponse`, not a generic graph:

- `success` must be true for the benchmark to proceed.
- `grid_data.pandapower_json` supplies the native pandapower topology. The
  benchmark loads this with `pandapower.from_json`.
- `grid_data.grid_id`, `seed`, `source_config.seed` and metadata
  `nodes`/`edges` support association and integrity checks. A shared grid ID
  alone cannot associate an execution.
- `loading_level`, `ref_sys_id` and other protobuf fields retain their original
  meanings/defaults. Missing proto3 fields can have defaults; this document does
  not invent proto2-style required fields. Qualification additionally verifies
  the captured seed/configuration, counts and exact network bytes.

For the benchmark, files are `benchmark-source.json` and `benchmark.json`.
The safe export includes `source_sha256`, `kpis`, `episodes`,
`scenario_count` and `upstream`. Upstream metadata records the **same workflow**,
source task, manifest digest and grid digest. The benchmark request must reference
that source output; the orchestrator's recorded input/output references must agree.

No conversion is inferred from equal content types. Protobuf parsing, the native
pandapower loader and original benchmark operation validate the data actually
consumed. The API collector rejects mismatched requests, manifests, seeds,
upstream associations, file hashes and changed previously accepted captures.

## Slots, cardinality and parameters

Binding: `generate-grid.captured_grid → benchmark-grid.captured_grid`.
Each output guarantees exactly one reference; the benchmark requires exactly one
upstream input. The generator has no data input in this qualified variant.
The benchmark's terminal output is `benchmark_capture`.

`seed` is an **execution parameter**, integer 42 or 43 (default 42). It is sent
through `http-parameters-v1`, not a workflow input or a second grid reference.
The benchmark publishes no editable execution parameters. Its node-owned
defaults and no-op baseline agent remain fixed; arbitrary algorithm source,
files, environment variables and network targets are not exposed.

`whole-output-v1` deliberately supports at most one input and output slot per
operation, no joins, cycles, projection, conversion or slot inference. Optional
inputs may be absent. Required inputs must be bound. Workflow-input routing is
not implemented for this transport and is rejected, rather than broadcast to an
unqualified slot.

## Domain and limits

Purpose: synthetic transmission-grid research and a software baseline benchmark.
The producer does not provide time-varying load/generation series; the consumer
uses a flat static profile derived from the generated operating point. This
behavior is documented in the original protobuf and implemented in
`_adapt_grid_data_to_config`; no converter or new scientific model was invented.

Seed, node/edge counts and topology are reproducible inputs/outputs for the pinned
algorithm. UUIDs, manifests containing workflow IDs and measured runtime seconds
are not expected to be byte-identical across executions. Only one new live run
was authorized; this is not a cross-run numerical reproducibility study.

KPI units and scientific validity are **not established**. Native pandapower
serialization is preserved, but units are not inferred from JSON property names.
The successful 11-step, no-op episode proves data delivery and execution, not
safety, operational optimality, benchmark coverage or physical-grid suitability.

Service ownership is attributed to the Dutch node by the existing catalogue
provider and authoritative source. The earlier export had null account/node
ownership and repository fields. The qualification profile uses an explicitly
labelled local owner mirror; genuine node-manager attestation and production
governance remain outstanding.
