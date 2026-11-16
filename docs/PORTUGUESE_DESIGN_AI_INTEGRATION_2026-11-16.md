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
