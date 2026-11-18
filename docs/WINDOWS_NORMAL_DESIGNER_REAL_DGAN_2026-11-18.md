# Windows normal designer CSV / real DGAN acceptance — 18 November 2026

Two ordinary browser Runs completed as a separately registered Solution Designer
account, using the same saved solution and selected CSV. These are fresh real DGAN
software-fixture executions, not the earlier source-API/DGAN-double tests and not
partner scientific approval. No workflow, task observation or submission was seeded.

## Implemented connection

An optional generic `algorithm-settings-v1` observation contract now connects the
configured runtime to the existing owned Portal result/preview reader. A separate
private observation key and explicitly installed target declaration are required.
Both node deployment copies and Portal use the same validator. It checks the
workflow/task/instance/operation, configuration/contract/input/source-response hashes,
requested/observed types and keys, model/weights/source/image digests, weight count
and observation basis. The existing receipt pinning, output-byte/hash validation,
target allowlist and ownership checks still run. Delivery alone never populates
algorithm-consumed settings; existing native algorithm evidence remains supported.

The development recorder wraps the real DGAN functions in the unchanged immutable
ML image, checks actual training arguments and freshly saved configuration, hashes
real weight tensors, and observes the actual generate call and loaded model.
An independent read-only process reloaded the new models and verified the same
model/weight hashes and saved settings. The full saved configuration has a separate
canonical SHA-256: sorted compact JSON, enum values represented by module/type,
member name and value. This supplemental inspection does not alter pinned receipts.

Results now display requested, validated submitted, delivered and observed values
separately, including delivery when stronger algorithm evidence is present. Evidence
details expose observation/model/weight/output hashes. CSV name and sequence/row
counts remain on that run's result. No service-ID or saved-workflow exceptions exist.

## Source and serving identities

Portal branch `codex/normal-designer-run-20261118` was fetched at
`744df92b04a1a6361491085995be95dfc82eb985`, based on published
`72e440c7003f6c210f3a13e7dd0d2c4b6b19c550`. This increment adds the observation
reader, visible delivery/model details, isolated workspace tools and evidence.

WP3 branch `codex/normal-designer-evidence-20261118` began at published
`7e16c810bd928a4bc13df16cb0fb7d712e6f57d8`. Git applied the supplied selected-CSV
patch, SHA-256 `eec0045eaf3eca8bf230c8b00a19786a5c7bb243f6c98c7408f068e67bb5a511`,
as `e038f55f23af66f5e93175fbc24560a5aab9ba71`; its exact tree is
`8aa7bab50d9d934ed9f333b4a8fda98ed89147e0`. This commit was published with Git.
The additional observation implementation is published as
`cbe1bbd8064dbd57655d28073bfec622aebbd752`, tree
`463d07484c65f1e7fb28a5143fb3e2d19e4c2c6c`. The published WP3 tip including
sanitised evidence is `69f7408e12908eb85a5de50af037e4f134e2be49`, tree
`7d5db96b182241546baafcb38b88bd2b031f56d3`.
The old WP3 and Portal branches/checkouts were preserved.

The additional [observation/evidence patch](../deploy/patches/wp3-algorithm-settings-observation-20261118.patch)
has SHA-256 `6b2cde7704612126aeaf80ab225d29be56dd5122423751cd8c6927fc6c842256`.
It was replayed with Git in a fresh detached worktree from `e038f55` and reproduced
the exact published final tree `7d5db96b182241546baafcb38b88bd2b031f56d3`.
Patch files now explicitly retain LF line endings on Windows, preserving canonical
Git byte hashes. [Patch provenance](verification/windows-normal-designer-patches-20261118.json)
records both separate bases, hashes and resulting trees; never reapply either blindly.

| Endpoint | Actual serving implementation |
| --- | --- |
| `http://127.0.0.1:23126` | New Node/Next frontend source copy; build source fingerprint `8d49ec7749a9a121200a1dc3f430cfbe1011a4233319a612d82e424371d29991`; production build including TypeScript passed; starter reported READY and browser/API health checked. |
| `http://127.0.0.1:28191/health` | New host Python Portal API from this development worktree; fresh development SQLite database, cookie and accounts. |
| `http://127.0.0.1:28192` | New host Python WP3 API and Worker using frozen paired source, authenticated by separate new keys. |
| `http://127.0.0.1:28193` | Authenticated configured Control connector; frozen WP3 common source plus existing qualification entry point. |
| ML, no host port | Real DGAN image `sha256:557246d79612eaa2106266d60cc6b36970634afebb659e371658cce6a1f1f61f` plus read-only observation instrumentation. The connector uses the same immutable base image with its separate mounted code. |
| Redis loopback `26380` | Image `sha256:8b81dd37ff027bec4e516d41acfbe9fe2460070dc6d4a4570a2ac5b9d59df065`, fresh authenticated AOF state. |

The new Docker project has fresh Redis/model/state/observation volumes, fresh
namespace and keys, a private ML network, read-only reviewed export mounts and a
new fixture input directory. No retained experiment volume was reused. Private mount
paths, keys, credentials, database and raw diagnostics remain in ignored operator
files. [Serving source manifest](verification/windows-normal-designer-source-20261118.json)
records exact serving bytes and committed-source hashes, explicitly distinguishing
Windows line-ending-only differences. A built frontend is a source snapshot, not a
claim that an unrelated image tag was upgraded.

## Browser designer acceptance actually performed

Provider/admin normal routes registered three new accounts, imported two distinct
services explicitly named **DEVELOPMENT SOFTWARE FIXTURE — TrainModel/GenerateData**,
reviewed their synthetic contracts, installed read-only qualification exports,
confirmed valid/invalid local software checks, approved the fixture services and
activated only these fixture contracts. Actual Portuguese partner drafts were not
activated or edited. Fixture bounds/defaults are explicitly synthetic (1–32), not
approved scientific settings. The valid/invalid operator qualification calls are
separate from the following browser Runs and do not replace them.

The independent designer signed in, selected catalogue services, connected the
workflow, opened Builder Deployment options → Run input → CSV data, selected a new
file, configured each instance and saved. A refresh/reopen retained the same solution
and selected file. Validate design and runtime readiness passed; each execution
required the on-screen **Confirm deployment** action. Both result pages were inspected.

Solution: `aef401a4-80f7-427e-8ebe-75a52a1d33cc`.
Input: `DEVELOPMENT-SOFTWARE-FIXTURE.csv`, 32 rows, first column `datetime`, finite
numeric `load` and `temperature`; SHA-256
`ad68eb1be631c27bc794f65a45c37a3897fe54f96d2f0d25d999a65c474b8f5c`.
The first-column/index arrangement and small shape follow the inspected source
implementation. Data/index selection remains separate from adjustable settings.

| Browser Run | Requested / delivered training | Actual saved-model settings | Actual generation |
| --- | --- | --- | --- |
| `wf-c155a6dd6853` | epochs 1, batch 16, sequence length 4 | epochs 1, batch 8, sequence length 4 | 2 sequences, 8 CSV rows |
| `wf-6066f56dcf4b` | epochs 2, batch 16, sequence length 4 | epochs 2, batch 8, sequence length 4 | 3 sequences, 12 CSV rows |

Batch 8 was observed independently in each current run's real model, not copied
from the earlier qualification or inferred from query delivery. Training and
generation share the same observed model and weights within each workflow; the
generation input hash equals its own training output hash. Each new workflow has
a different model and weight hash. [Sanitised run evidence](verification/windows-normal-designer-real-dgan-20261118.json)
contains requested/delivered/observed settings, immutable submission/configuration,
contract, input/model configuration/weight/output hashes and all task associations.

After the second edit/Run the original page still showed epoch 1 and 2 sequences /
8 rows. Read-only reinspection confirmed its original snapshot, pinned observations
and output bytes unchanged, including after a restart of only this new host workspace.
The normal Save action rejected epoch 0; reopening retained valid epoch 2. The
database still contains exactly the two browser workflows, confirming no extra Run.
Another designer received 403 for submission, evidence, real orchestrator tasks and
owned preview. No authenticated target or task association was bypassed.

This is browser automation using an independent designer account. It is not a claim
that an unaided human or Portuguese scientific owner has accepted the product.

## Tests and boundaries

| Verification | Current result and limit |
| --- | --- |
| Portal observation/owned results/selected CSV/saved-solution assistant tests | 64 passed; explicit observation/assistant doubles where labelled. |
| Reusable parameter onboarding/compatibility/discovery/instances | 63 passed initially; one source-path skip subsequently rerun and passed with matching WP3 source (64 checks verified). |
| Older WP3 / connector CSV capability gates | 2 passed; explicit HTTP response doubles, no dispatch. |
| Existing native evidence regressions | 16 passed; preserves actual-algorithm evidence path. |
| WP3 source connector/observation/Control/client/instance configuration | 106 passed; source API binding uses an explicit DGAN double. These tests do not establish real model acceptance. |
| Rendered results/CSV picker/saved-solution assistant components | 9 passed, plus submitted-settings assertions; no browser claim from component tests. |
| Real model | Two fresh browser Runs, four real processing tasks; independent saved-model reload verified configuration/weights. One separate fixture qualification train/generate pair also exists. |
| Browser/user path | Sign-in/catalogue/select CSV/configure/save/reopen/validate/preflight/explicit Run twice/results/invalid save/original result verified through UI. |
| Build and provenance | Next production build including TypeScript; five canonical validator/provenance exports; frozen paired source checked. |

Existing FastAPI/Pydantic/SQLAlchemy dependency deprecation warnings remain.

## Preserved work and release gaps

Retained demo `http://127.0.0.1:23124/login` remained HTTP 200 with the same container
`9ddf40c4224bfa8ee561684aa6e891791819149d899cae7d8c481674ff654d7c` and image
`sha256:a7ca1100fb5364ca876117a176b351f411bb330f5baa8dfe6a4f09de49d635ed`.
Guarded review `http://127.0.0.1:23125/login` remained HTTP 200; its restrictions were
not removed. The original Portal branch/SHA and 150 dirty entries remain; no switch,
reset or stash occurred. Old models/state/results/evidence and closed spending scopes
were preserved. No production deployment, paid provider call or paid installation.

Remaining owner gates: production data/index semantics, scientific suitability,
accepted settings/defaults/limits and supported runtime installation. This is a
development software fixture with source-derived test shape, not partner approval.
Remaining release/product gates: PostgreSQL/migration/rollback/staging acceptance,
independent human acceptance, a second independently onboarded service-family browser
acceptance, useful multi-input composition, and clearer legacy untyped connection
presentation (Builder currently says no declared slot binding while validated legacy
DataReference flow executes). Raw ML remains private; production exposure is not approved.

Design with AI still edits the same saved solution through the shared writer and
Run path. Offline assistant tests use explicit doubles. The new workspace visibly
reports AI disconnected; no successful LLM reply is invented. The
[bounded genuine-conversation acceptance](GENUINE_CONVERSATION_ACCEPTANCE_2026-11-18.md)
is prepared for separate concrete paid approval; no grant has been created or enabled.

## Simple demonstration

Open [the first result](http://127.0.0.1:23126/deployments/wf-c155a6dd6853#results)
and [the second result](http://127.0.0.1:23126/deployments/wf-6066f56dcf4b#results).
Compare epochs, batch requested/delivered/observed, and generated sequence/row counts.
Expand Evidence details to see that each result has its own model/weight/output hashes.
Open [the saved Builder](http://127.0.0.1:23126/builder?solutionId=aef401a4-80f7-427e-8ebe-75a52a1d33cc)
to continue editing; another execution still requires explicit Run confirmation.
