# ConfigureAndSynthesize instance parameters — owner review draft

Baseline: paulban/ai-effect-wp3 **ba598b2459f9986dac4e37dcc5d7d3298f25dc3a**.
Proposed target: the source-backed imported Dutch generator family. This is not
an owner-approved production selection or activated registry contract.

The patch implements the existing **http-parameters-v1** configuration envelope.
Its validator is the exact portable artifact used by maintained WP3
**0221b7ecd4a2d5f072de640350ebc599df22131a**, SHA-256
**1861736c1bd9c8a1e4d3aa86b1a2f58ef27bf5e272d682a619062cfb8b7171aa**.
Provenance is in parameter_contract_provenance.json. No second transport,
orchestrator patch, adapter framework or service-name map is introduced.

## Requests and capability

Before: the deployed ExecuteRequest has no configuration field, so this JSON
override is ignored by Pydantic and the operation uses default seed 42:

~~~json
{
  "method": "ConfigureAndSynthesize",
  "workflow_id": "example-only-not-submitted",
  "task_id": "example-generator",
  "inputs": [],
  "configuration": {
    "contract_id": "unconfirmed-review-contract",
    "contract_version": "0.2.0-draft.1",
    "operation_identity": "urn:aieffect:proposal:nl:imported:ConfigureAndSynthesize",
    "schema_version": "1.0",
    "parameters": {"seed": 43},
    "instance_id": "review-generator-instance"
  }
}
~~~

After: the **same request shape**, issued only after normal capability/registry
review, validates the envelope and delivers 43 to InputConfigurator(seed=43)
and PowerGridGenerator(seed=43) through the existing combined handler.
These example IDs are not production IDs or approval to submit an experiment.
contract_id is the portal's registry-row reference; the established runtime
handshake matches operation identity/version and parameter schema, not a local
copy of the registry. No production contract row is created by this patch.

GET /control/capabilities returns capability_schema_version=1.0,
transports=[http-parameters-v1] and just ConfigureAndSynthesize with proposed
operation identity above, contract version **0.2.0-draft.1** and:

~~~json
{
  "schema_version": "1.0",
  "transport": "http-parameters-v1",
  "properties": {
    "seed": {
      "type": "integer",
      "title": "Random seed",
      "description": "Nonnegative seed within signed-int32 storage; scientific suitability is unverified.",
      "minimum": 0, "maximum": 2147483647, "default": 42
    }
  }
}
~~~

ConfigureGrid and SynthesizeGrid do not advertise this new capability.
Benchmark behavior and declarations are unchanged. No consumption-evidence
protocol, whole-output compatibility or scientific qualification is claimed.

As in maintained WP3, the configuration envelope contains already validated
**effective** values. With no configuration field, default seed 42 is retained.
For a configured default, the producer sends parameters={seed:42}; an empty
parameters object is rejected rather than deviating from the existing handshake.
A bare top-level parameters object (including null) is explicitly rejected,
not treated as another way to bypass identity/version checks.

## Validation and legacy behavior

- Only JSON integers in the declared range are accepted: bool, string, float
  (including 43.0), null, negatives, overflow and unknown settings fail.
- Envelope schema/contract/operation mismatches, unsupported transport/schema
  declarations and unknown/missing envelope fields fail before algorithm calls.
- A combined legacy inline configuration must be one well-formed base64 JSON
  object with unique keys and known existing configuration fields. Invalid
  seed values, malformed/non-inline/multiple inputs and duplicate keys are
  explicit errors, not defaults.
- With an envelope, legacy inline configuration may still supply topology,
  loading and reference-system fields. **Any inline seed plus envelope seed
  is rejected, even if equal**: there must be exactly one explicit seed source.
  Other legacy configuration semantics are unchanged; this patch does not
  create a complete validation contract for all topology/physics inputs.
- Valid legacy inline calls and unconfigured ConfigureGrid/SynthesizeGrid remain
  compatible. Combined-operation HTTP validation errors return 422 without
  replacing previous task status/data or config/grid caches.
- Direct gRPC positive seed delivery remains unchanged. Negative seeds now
  explicitly return INVALID_ARGUMENT before any generation/cache mutation.
  An omitted or zero proto3 seed still selects default 42, because the existing
  scalar has no presence distinction. No protobuf definition was changed.
  HTTP can explicitly select zero; owners must confirm this documented interface
  difference before approving the contract.

## Bounds provenance and limits of the evidence

GridSynthesisRequest, GridSynthesisConfig and GridData use signed **int32** seed
fields in this baseline's proto/data_synthesizer.proto. The retained local
baseline dependency image contains powergrid_synth **0.1.1**, source commit
**b36740438a95db60d30f3681daa72a26e1d2dd73** of
TU-Delft-AI-Energy-Lab/grid-synthesizer. Inspection of installed source shows:

- InputConfigurator.__init__: numpy.random.default_rng(seed).
- PowerGridGenerator.__init__: random.seed(seed) and numpy.random.seed(seed).

The [NumPy legacy RNG contract](https://numpy.org/doc/stable/reference/random/legacy.html)
allows scalar seeds from 0 through 2**32-1; signed-int32 storage narrows the
nonnegative intersection to **0 through 2,147,483,647**. See also the
[protobuf scalar/default-presence rules](https://protobuf.dev/programming-guides/proto3/).
This is a proposed representational bound, not an assertion that every seed
produces a valid, convergent or scientifically acceptable network. No [42,43]
enum was copied. Dependency provenance is specific to that retained test image;
the partner's Dockerfile currently has floating base/package inputs, so it does
not establish the library revision inside every deployed production image.
The owner must confirm actual deployed dependency identity and supported seed
semantics. Remote library files were not retrievable through the connector:
the commit and constructor calls above came from installed distribution
metadata/source, not a fresh partner attestation.

## Focused checks

Run with existing service dependencies, without starting main.py:

~~~text
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/tmp/mpl python -m unittest discover -s tests/unit -v
~~~

The suite uses the actual FastAPI routes, Pydantic envelope, combined and
individual handlers, actual generated protobufs and direct in-process gRPC
servicer calls. InputConfigurator, PowerGridGenerator, every physics stage,
pandapower conversion and the inter-service fetch are narrow test doubles.
Tests forbid socket connections, gRPC channels and HTTP fetches; the recorded
run also used Docker --network none, a read-only checkout and disposable tmpfs.
No new service image or dependency installation is required for that check.
Assertions verify constructor arguments, effective configuration and synthetic
protobuf propagation only. The tests' completed mock response is not a real
algorithm result, workflow execution, qualification or independent usability.

## Deliberately unresolved

GetGridConfig/GetGridData still expose process-wide latest caches through empty
requests. The combined path still retrieves configuration through its existing
gRPC reference; concurrent calls can race. This patch does **not** establish
task-specific snapshots, immutable same-grid benchmark association or safe
concurrent execution. No benchmark, protobuf, output-binding or portal/runtime
guard was changed. Newly composed execution must remain disabled.

## Dutch-owner decisions

- [ ] Select the source-backed imported family or supply an authoritative
  alternative; no production selection is implied by this review.
- [ ] Confirm deployed generator/library identities, seed semantics and bounds,
  including HTTP zero versus omitted/zero direct-gRPC behavior.
- [ ] Approve the existing envelope/capability protocol and proposed identity/
  version, effective-default rules, strict rejection and dual-source policy.
- [ ] Review tests and patch against the exact baseline; coordinate any partner
  publication/deployment separately. This patch is not pushed to the partner.
- [ ] Keep contract activation and composed execution blocked until the remaining
  owner/review/immutable-association/runtime gates are separately satisfied.
