# Platform-controlled parameter verification

Reuses the existing AIE-37 qualified profile and platform-authored runtime.py,
capture_algorithms.py, contracts.json and immutable CaptureStore. These were
already maintained before this milestone. No partner implementation is copied
from the separate Dutch parameter patch. Its pinned baseline has no LICENSE,
COPYING, AGENTS.md or CLAUDE.md in the recorded tree; no new redistribution right
is inferred. The partner patch stays a separate unconfirmed owner-review artifact.

Local retained base images and dependency commits remain those pinned by
app/services/dutch_capture_contract.py and the prior qualified capture records.
They are reused locally, not published as new partner/production images.
This reference implementation is platform controlled, not Dutch-owner approved.

The unchanged local-only contracts expose only seed 42 or 43. The maintained
http-parameters-v1 validator and whole-output-v1 immutable reference negotiation
remain authoritative. InputConfigurator.create_params and
PowerGridGenerator.generate_grid now each record the constructor's seed only
after the real method returns. Invalid or conflicting settings are rejected
before a capture claim is created. Failures after dispatch remain preserved.

The task authorizes at most two new qualified executions, one per seed. Use
disposable owned saved copies and two distinct normal one-use execution grants.
Never retry an uncertain/failed submission or reuse a consumed grant. Do not
give composed designs this qualification. Provider keys stay disconnected and
the existing monetary/count ledger remains read-only at 13/13.

Focused runtime tests use algorithm doubles; only separately identified local
execution captures can establish real consumption. Historical captures keep their
original submitted runtime pins and are never rewritten for new instrumentation.
Exact-grid benchmark association uses workflow/task manifest and grid hashes,
not the partner's latest cache.
