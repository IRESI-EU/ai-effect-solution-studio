# Portuguese results and registered Design with AI integration

Starting review: Portal e252f0221e80781e4b6d1754960eff9d6c3ce54c,
maintained WP3 4a4bdc8f1150d44d809b0b281765a114f695c71d. This is a
non-executing extension; earlier successful/failed acceptance records remain intact.

## Checkpoint 1 — authenticated generated CSV

The results panel exposes **Download generated CSV** only for a verified
GenerateData instance. The owner-authorized endpoint resolves the exact immutable
workflow/task, reruns the existing signed-capture, producer-model, dataset and CSV
integrity checks, and serves those same validated bytes as an attachment. It takes
no URL or path, exposes no service credentials and needs no live worker/algorithm.
Generic remote preview remains blocked. A missing/corrupt/misassociated artifact
cannot be downloaded. Responses use private/no-store, nosniff and a sandbox CSP.

Focused isolated download/evidence and existing Dutch-download regression suites:
45 passed (existing deprecation warnings). Windows temporary-directory setup failed
before tests on the first attempt; the corrected directory run above passed. A
fresh read-only snapshot confirmed all ten existing designs, nine completed journal
jobs, four closed scopes, stopped workers, no unresolved queues and the unchanged
25/25 provider ledger. The actual owner browser downloaded **Download generated CSV**
from http://127.0.0.1:23124/deployments/wf-717110fb8d5e#results: 41,826 bytes,
SHA-256 `553c7acca074de4dde804dfcf4af25f23252987df79dc31f20da39f6bbb05540`,
exactly the preserved artifact. [Rendered evidence](../deploy/portuguese_sandbox/evidence/design-ai-20261116/generated-csv-download.png).
Workers remained stopped. API/web served source
`66faa6c2c1202909abd8ff1645d38d370dbd7ed2`, respectively images
`sha256:9e823760cccf80ce7f6f1db75c9a3d41f7121d8cc737531a8937c69423c84643`
and `sha256:ceee60fd6def9d1262b88829c07b18571e7cede2aba86fcd7a5a132531d875ba`.
The offline web packager passed its 18 checks, typecheck and production build.
A verified consistent PostgreSQL dump, previous compose configuration and container
identities are retained privately in `local-backups/pt-ai-download-20261116`;
previous images remain available for rollback. No migration was required.

## Registration finding

The retained API currently has DESIGN_AI_ENABLED=false and an empty operator
template-registration policy. A saved solution is not registration authority.
The existing operator-controlled template policy is the registration mechanism;
it does not publish or approve a shared workflow. The bounded extension will pin
a reviewer-scoped experimental entry and revalidate services/contracts/binding and
source ownership. No Portuguese-owner attestation or execution authority is implied.

## Checkpoint 2 — bounded registered configuration

Implemented an explicit `registered_parameters` entry in the existing operator
template policy. It is limited to the configured sandbox reviewer, that reviewer's
unchanged source digest, the two experimental chained service IDs, both active
0.2.0 contract-definition hashes and the source's published model_ref binding.
The preparation operator verifies existing actor/owner/service/contract permissions
read-only; it neither publishes a shared solution nor changes approval/account rows.
Installing the reviewed record is a local operator configuration action, not a
Portuguese-owner attestation or execution grant.

Registered discovery supplies authorized public operations, declared parameter
schemas/defaults and the opaque sandbox dataset choice. A typed recommendation can
select only those settings. Create allocates new node/edge/solution identities,
uses declared defaults (1 epoch, batch 4, count 10) and clears inherited workflow
input, results and authority. A non-default recommendation stays a reviewable
proposal until explicit selection of the authorized Training CSV allows Apply.
Missing CSV is visibly required. The explicit configuration controls also work with
AI disconnected; they generate no assistant response or pretend interpretation.

Parameter/input changes reuse `design_ai.propose/candidate/apply/undo/save`,
the canonical parameter validator, input authorization, whole-output binding checks
and workflow compiler. A real count10→20 proposal can be Applied, Undone (including
input), reapplied with the same identities, Saved and reopened in Builder. Only
the registered configuration scope may select its authorized CSV; legacy settings
copies retain their fixed-input restriction. Source/contract/approval/ownership or
revision drift denies mutation. Save never submits a workflow.

The generic native-only composer remains separate. Its existing external-input
regression exposed a pre-existing missing first-operation input guard (the file was
unchanged from the starting head). The narrow guard now enforces its documented
no-external-input scope; sidecar/adapter exclusions are retained, not removed.

Verification: the integrated discovery/targeted-edit/composition run had 96 passes
and that one external-input failure. After correction, 59 focused registration,
external-input/compatibility and historical evidence cases passed; the operator's
final canonical read-only check passed separately. Frontend session/evidence checks
16 passed; actual-page/recommendation/workspace checks 19 passed and typecheck
passed. Existing deprecation/module warnings remain. These are isolated SQLite and
deterministic provider/runtime doubles, not PostgreSQL concurrency, genuine AI
interpretation or algorithm evidence. No full backend inventory is claimed; older
baseline reports remain historical. Final packaging/browser observations follow
as a separately identified checkpoint.

### Local registration procedure (design only)

With the new API image and existing profile mounted/configured, run:

```text
python -m app.services.registered_parameters_operator --reviewer-id <existing-owner-uuid> --source-id b4e48556-c3a5-4a73-903d-c2a2618756fd --registration-id pt-reviewer-chain-v2-20261116
```

Review its policy output, preserve the previous configuration privately, and merge
only its `portugal` entry into `DESIGN_AI_TEMPLATES`. Enable design controls only for
the existing reviewer using `DESIGN_AI_RESTRICTED_BETA`/`DESIGN_AI_REVIEWER_IDS`.
Keep provider key disconnected, supervised flags disabled and all workers stopped.
Record attributable before/after hashes. No bootstrap, database migration, workflow
registration rewrite, account/permission change or execution authorization is part
of this procedure. Removing the policy revokes its AI draft mutations; saved owned
Builder designs and historical evidence remain separate.
