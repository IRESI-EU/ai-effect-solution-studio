# Reusable module instances — AIE-18

Registry-owned typed definitions pin each instance to an operation contract and
version. Builder exposes typed settings and independent copies; the compiler
validates values/defaults and creates stable instance aliases and bindings.
Configured HTTP execution requires advertised compatible capabilities. Unsupported
or drifting declarations fail closed; there is no silent downgrade to defaults.
Unconfigured legacy workflows retain their original path.

Immutable submitted snapshots distinguish requested, effective and observed
algorithm-consumed settings from the current editable design. Historical records
remain tied to their original source/image versions. External service task IDs
are associated explicitly rather than inferred from instance or runtime IDs.

## Dependencies and provenance

Stacked on the Design with AI foundation PR. Requires the companion maintained
WP3 HTTP configuration PR, which depends on its separately identifiable legacy
ControlClient correction. The canonical portable validator is
apps/api/app/services/parameter_values.py; WP3 vendors the exact bytes as
orchestrator/src/services/parameter_contract.py, with a digest provenance file.
The operation registry owns definitions; WP3 contains no Dutch/Danish node map.

The first implementation commit also retains the unpublished guided-draft and
recorded-result prerequisites on which instance editing depends: per-draft browser
state, normal copy/save lifecycle, immutable local evidence and allowance display.
It is reconstructed from the preserved pre-conversation source checkpoint.

## Verification categories and limitations

Portable API/HTTP/Redis fixtures verify validation, identity, privacy, revisions,
compatibility rejection, immutable history and rollback behavior. PostgreSQL tests
are a separate suite and require disposable local databases. Prior local Dutch and
Danish executions established algorithm consumption for their original settings;
they do not prove that a newly edited limit-4 design has run. Retained two-case
real-provider evidence verifies only the two prepared prompts. Neither fixtures
nor retained evidence establishes broad model quality, independent first-time-user
usability or production compatibility. AIE-18 remains In Review.

No production deployment or new model/workflow request is part of publication.
Raw runtime exports, account details, private addresses/configuration, spending
ledgers, checkpoints and local operational reports are excluded from Git review.
