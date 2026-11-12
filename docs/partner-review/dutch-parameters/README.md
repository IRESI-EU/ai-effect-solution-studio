# Dutch instance-parameter delivery patch — 12 November 2026

**Implemented locally; partner review only. No partner push, deployment or contract activation.**

| Identity / check | Result |
|---|---|
| Partner baseline | paulban/ai-effect-wp3 ba598b2459f9986dac4e37dcc5d7d3298f25dc3a |
| Local-only patch head | c08c86aa09a577915cec5d868c7deef73ec408ad, branch codex/dutch-instance-parameters |
| Portal starting evidence | 0b8ae6afa2cc4fc933dfa1a50ae0cbc4178d9c07 |
| Cumulative patch | [ba598b2-instance-seed.patch](ba598b2-instance-seed.patch), 8 generator-only files |
| Patch SHA-256 | 50053dc76cdef523ef3b5375c2e795f12063bc088ebb6af07d65194b3e26b960 |
| Replay | Exact-baseline alternate-index apply passes; resulting tree a4fa39166c8750517b623ddc35ec36910f77700d equals local patch head |
| Focused tests | **24 passed**, no failures/errors/skips; 0.768s test runner, existing NetworkX future warning retained |
| Registry integration | Proposed contract validates through OperationContractWrite; schema round-trip parameter digest matches runtime capability |

The [patch](ba598b2-instance-seed.patch) contains the actual control/handler changes,
exact shared validator and provenance, tests and owner documentation. It is a
cumulative plain Git diff against the exact baseline, not a patch against only
the last metadata follow-up commit. No protobuf or benchmark file changes.

The generator accepts the maintained AIE-18 **configuration** envelope, negotiated
by GET /control/capabilities. Only ConfigureAndSynthesize advertises support.
Strict seed typing/bounds, operation/schema/contract checks, unknown-setting
rejection and explicit dual-source rejection happen before generation or result
mutation. Omitted override stays 42. Valid 43 reaches both constructor call sites
through the actual route/handlers, as observed with algorithm doubles.

The proposed HTTP range **0..2147483647** comes from the installed library's NumPy
seed constraints and existing signed-int32 protobuf storage. It is not a [42,43]
enum or a claim that every seed produces a scientifically valid network.
Direct gRPC keeps positive-seed delivery and omitted/zero -> 42 behavior;
negative seeds now fail explicitly. Owners must approve these semantics.

See [owner review and before/after example](OWNER_REVIEW.md),
[request JSON](request-example.json), [capability proposal](capability-proposal.json),
[contract proposal](contract-proposal.json) and [verification evidence](verification.json).
The proposed operation/version is unconfirmed **0.2.0-draft.1**; no active
production pin or owner attestation is manufactured. Binding transport remains
null, so this does not advertise a fully compatible generator/benchmark pair.

## Reproduce for review

In an isolated clean partner checkout at the exact baseline, use the local patch
path below. These are review instructions, not commands run against production:

~~~text
git switch -c codex/review-dutch-parameters ba598b2459f9986dac4e37dcc5d7d3298f25dc3a
git apply --check <absolute-path>/ba598b2-instance-seed.patch
git apply --index <absolute-path>/ba598b2-instance-seed.patch
cd use-cases/dutch_node/data_synthesizer
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/tmp/mpl python -m unittest discover -s tests/unit -v
~~~

Use existing service dependencies. The recorded run reused retained image
sha256:f14731e7c4bf273561ad02ab2a42895069543b7b6e0f0ffa2dec4fb56599b992
with no pulls/builds, --network none, read-only source and tmpfs scratch files.
Python 3.10.22, NumPy 2.2.6, powergrid_synth 0.1.1; installed library commit
b36740438a95db60d30f3681daa72a26e1d2dd73. The host lacks scientific/gRPC
dependencies, so no packages were downloaded to it. Existing network pipeline
scripts were inspected but not run. No applicable AGENTS.md/CLAUDE.md exists in
the pinned partner tree. Partner source checkout contains only the selected
generator subtree and root documentation; existing work is preserved.

This verifies **argument delivery and validation**, using doubles for synthesis,
physics, conversion and inter-service I/O. No real algorithm, provider request,
workflow or scientific qualification occurred. Registry schema checking initially
caught missing title/description metadata; that was corrected before the final
24-test run and digest round-trip. Earlier runs overlap and are not summed.

## Remaining decisions and boundaries

- Dutch owner selects the authoritative service family; the imported family is
  only the proposed target.
- Owner confirms actual deployed dependency identity, seed bounds/zero semantics,
  strict envelope/capability identity/version and the reject-both-sources rule.
- Owner authorizes any partner publication and later deployment separately.
  Only the portal's existing draft review receives this package.
- Latest-cache retrieval is **unchanged**: no task-specific immutable snapshot,
  same-grid benchmark guarantee or safe concurrent execution is established.
  Whole-output contracts, immutable association, normal sign-in, accounting
  transport and cumulative code review remain release gates.

Newly composed execution remains disabled. Existing portal runtime source,
accounts, demonstrations, captures, production registrations and spending ledger
are untouched; **13/13**, zero new calls/spend, zero allowance changes.
Local source/log locations under the original checkout are
local-backups/dutch-parameters-20261112/ and
local-backups/dutch-parameter-evidence-20261112/. No credentials are included.
