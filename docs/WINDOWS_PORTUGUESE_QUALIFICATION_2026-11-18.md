# Windows Portuguese qualification — 18 November 2026

Implemented the owned authenticated Control result/receipt connection and completed two disposable **real DGAN** fixture runs. This advances the earlier source-wiring checkpoint; it does not approve scientific limits, activate provider contracts, qualify every node runtime, or establish a normal designer Run or paid conversational acceptance.

## Source and environment

| Checkout / image | Inspected identity |
| --- | --- |
| Original Portal (preserved dirty) | `feature/design-with-ai-pilot`, `12aae82dd47b078ba077aca40b0712c375b9d7f3` |
| Isolated Portal development baseline | `codex/reusable-provider-onboarding-20261117`, `8a15bce707e8222a14f03b91c452d6977bea10be` |
| Original WP3 (preserved, untracked Danish directory) | `main`, `486ccc702bb2afca79fb7d31258d62ee0f94dbfc` |
| Existing Portuguese WP3 sandbox base (preserved) | `codex/portuguese-parameter-sandbox`, `d533219426af9ea6defaf0bc78956741201a5109` |
| Reproduced WP3 patches | Native commit `6bba4d069fe3992c5a98d1348823431096c44974`, Portuguese commit `ee0e134c079a1ab178a0ff43078e210d19d89091` |
| Reproduced Portuguese tree | `d54bbfc62fa6f054a7e1d276ae1ab4092dcb980b`, exactly the handoff tree |
| New isolated WP3 branch | `codex/portuguese-runtime-qualification-20261118`, `7e16c810bd928a4bc13df16cb0fb7d712e6f57d8`, tree `45ea7dbf869f5883aa7ef6de90d859cb5c586a23` |
| Upstream Portuguese checkout (clean, read-only) | `main`, `7ba677f7f0a93b5ed6126e43a0b7b0e30f59d6b3` |
| Inspected and qualified ML image | `pt33-tef-integrated-synthetic-data:latest`, pinned `sha256:557246d79612eaa2106266d60cc6b36970634afebb659e371658cce6a1f1f61f` |

The canonical Git patch bytes were verified before application. Windows checkout conversion produces different CRLF file hashes; those are not substituted for the published LF patch hashes:

- Native patch: `50ebfbf1a866d8584b249f93c582f7dab0286c2c2e34ed65b26d8d73d26d0a09`.
- Portuguese patch: `6f85f87d68a23398613952020021a558866c3dd2ead8c5d6baa89f3093ace40c`.
- New third [Windows journal-lock patch](../deploy/patches/wp3-windows-receipt-locking-20261118.patch): `8b9e2c35a8c1a867cf0b84ca9bbd1c3e4c2426a641df9df6ac837a5b58919aff`. Apply after the two original patches; they remain unchanged. Reproduced commit SHAs differ from the original authors' SHAs because `git am` creates new committer metadata; the reproduced tree was exact.

## Actual source/API agreement

The live image's `/openapi.json` hash is `7df3d50126b5730f3e5939d220bebd11f8a2cbad9ff5c832027747b2bc56b687`. Its integrated `main.py` exactly matches the WP3 source blob, SHA-256 `0e4caddd200e5366b504c3cce2df957fbd6a97beb4418b25613fa8d778e6e322`. Its `dgan.py` exactly matches the local upstream working file, raw SHA-256 `0a027576bb25656e4541dd822bf0f2395a79bb1cb377e1d11fb509dca9f79d54`; its Git/LF form is `e1a607ac01e94aa80e9e9c6beffef673ba0bd018ae44138788edd2e7f62ba184`. The upstream API lacks the WP3 integrated Control addition; it is not claimed to be byte-identical to the integrated API.

`POST /train` takes multipart `uploaded_file` and query `user_id`, `model_name`, `index_col`, `overwrite`, `sequence_len`, `batch_size`, `epochs`. The settings are integers. Identity/model/index are strings and overwrite is boolean. `GET /generate` takes `user_id`, `model_name`, integer `number_of_examples`, and boolean `return_csv`. The legacy `username`/`max_epochs` names are incompatible. Training waits for actual training and model saving before responding; generation loads the model and constructs the CSV before responding. The OpenAPI response schema itself is loose; an HTTP 200 alone cannot prove completion or model consumption.

Source defaults (`epochs=10`, `batch_size=1000`, `sequence_len=100`, generation count 1) are candidates only. No source-defined scientific bounds were found. The implementation stores `model.pt`, `features.csv`, `indices.csv` and a progress file under `models/<user>/<model>`. It drops incomplete trailing sequences and clamps batch size to complete sequence count. A selected index column is required in practice: the persistence code saves indices unconditionally. The feature-label/type selection assumes the index is first. Our fresh fixture uses `datetime` first and two finite numeric features; suitability of partner datasets, other indices/types and solar hyperparameter selection remains owner work.

Actual packages: Gretel synthetics `0.22.20`, CPU PyTorch `1.13.1+cpu`, NumPy `1.23.5`, pandas `1.5.3`, FastAPI `0.115.14`. Qualification executes the unchanged source/API and real DGAN. The opt-in probe wraps real train/save/generate calls, records real effective config, deserializes only the newly produced model, and counts saved weight tensors. It never replaces the model with a double.

## Isolation and recovery observations

The new Docker project is `aie-pt-qual-5bef0196d5fb`. Its private network, model/state/observation volumes, namespace, random Control key, input directory and provider-review accounts are separate from all retained experiments. Qualification exports were obtained through normal owned provider review and mounted read-only with `CONTROL_PARAMETER_QUALIFICATION_MODE=true`. Both contracts remain draft; all provider attestations remain false.

Docker initially copied a bundled model from the image into a fresh volume. Before any training, that volume was compared with the untouched image seed and preserved unused. The actual runs use a new **nocopy** empty model volume. Raw ML has no published ports. Only authenticated Control is bound to loopback `28190`; its second project network permits Docker's loopback port publication. No old model volume was mounted in the new project.

An initial startup request failed before dispatch (`ConnectError`, `dispatch_started=false`). Its journal remains. After proving no model/observation existed, the harness waited for upstream readiness and used new task identities. No unresolved dispatch was retried or erased. Both successful outputs and the failed journal remain in the dedicated state volume.

After qualification, the original connector source was frozen from the reproduced checkpoint in ignored read-only storage. Only the new qualification connector was recreated, after checking every journal was terminal. The real model run qualifies the checkpoint tree above, **before** the Windows locking follow-up. That follow-up changes journal synchronization, not model behavior; its source regressions are a separate claim.

## Results and implementation

| Verification | Result / limit |
| --- | --- |
| Real-model fixture run A | 1 epoch; requested batch 16, saved effective batch 8; sequence length 4; 2 generated sequences / 8 rows |
| Real-model fixture run B | 2 epochs; requested batch 16, saved effective batch 8; sequence length 4; 3 generated sequences / 12 rows |
| Model evidence | Different saved model hashes; real generator/discriminator tensors; saved config matches observed effective config |
| Invalid/replay/retention | Boolean epoch rejected without journal/dispatch; replay denied; earlier output bytes unchanged |
| WP3 source wiring + native Control | 41 passed, including new Windows reader/replacement race regression |
| WP3 Control client/configuration | 50 passed |
| Portal ownership/results | 60 passed, including actual authenticated fixture CSV/receipt reads |
| Saved-solution assistant, onboarding/discovery, configuration/compatibility | 72 passed; assistant responses are explicit offline doubles |
| Optional Danish native Portal journey | 2 skipped: native Redis/redislite executable unavailable on this Windows test host |
| Shared validator | All five source exports and provenance match |
| Provider workspace | Starter READY; real frontend build, API health and browser sign-in page verified; provider authenticated draft review/export succeeded |
| Normal designer execution / real conversational AI | Not established by this pass |

The Portal reader uses existing deployment ownership, immutable submission and task/input associations, plus an operator-installed endpoint for the same recorded runtime. It derives only the exact configured task data/receipt paths. It refuses arbitrary URLs, cross-runtime endpoints, redirects, proxy inheritance, conflicting observations and overlarge responses. Authenticated receipts and output hashes are pinned using existing `InstanceEvidenceReceipt` rows. No service IDs receive exceptions. File/inline preview and historical capture guards remain intact.

Receipt availability means **authenticated runtime delivery and output integrity**. The reader deliberately does not populate `algorithm_consumed` from an HTTP receipt. The actual model qualification is in the separate evidence record. The live-result integration test uses an isolated SQLite owned submission and explicit task-observation fixtures; it does not claim a full WP3-to-Portal designer Run.

Normal provider review still serves the generic shared Builder/Design with AI saved-solution path. Offline regressions verify review/apply/manual reload/undo against the same solution and explicit execution boundary. No paid assistant provider was called and no closed grant/spending scope was reopened.

## Working URLs and next demonstration

- Retained meeting demo: [http://127.0.0.1:23124/login](http://127.0.0.1:23124/login), original web container `9ddf40c4224b` still running. Saved designs/results, original dirty files, old model volumes and historical evidence were not modified.
- New guarded provider review: [http://127.0.0.1:23125/login](http://127.0.0.1:23125/login); API health [http://127.0.0.1:28189/health](http://127.0.0.1:28189/health). READY was observed from the existing Python launcher. The initial Windows PowerShell wrapper was read, but it was not itself launched; its equivalent Python launcher was used with existing dependencies and isolated local paths. Review build source is baseline `8a15bce`, not a claim of a new runtime UI deployment.
- Qualification Control: `http://127.0.0.1:28190`, bearer-authenticated; raw ML stays private. This is an operator endpoint, not a designer UI.
- Existing staging: `https://127.0.0.1:24443`, unchanged; no new staging/production deployment was performed.

Next simple user demonstration: sign into **23125** with the new private `provider_portugal` review account, open Publish, select **REVIEW COPY - model_trainer1 / TrainModel**, and inspect the saved draft. Its 1–32 bounds are explicitly software fixtures, not owner-approved limits. Refresh to verify persistence. A designer Run remains blocked until owner-confirmed data/index/semantics and reviewed runtime installation/activation are complete. A real paid conversational acceptance remains separately unauthorized.

Private credentials, source snapshots, full receipts, mount source paths, test packages/logs and compose configuration are in ignored `local-backups` directories only. Do not paste their contents into reports. The [sanitized model evidence](verification/portuguese-real-local-qualification-20261118.json) contains settings, model/input/output hashes and task associations; the [runtime inventory](verification/windows-runtime-inventory-20261118.json) contains exact inspected image/container identities and sanitized mounts/ports.
