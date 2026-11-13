# Connected Portuguese phase — existing-profile operator runbook

This is an additive update of ai-effect-pt-parameters, not a new profile.
The original three jobs and old one-training/two-generation scope stay exhausted.
Do not rerun the initial profile initializer or bootstrap.

Source checkpoint: Portal 654f3a68481738c902e9673d2f35f9c95715a6e9;
maintained WP3 30e1ac403c7434149f3ff3568843f2cc75702413.
The exact image IDs are constants in apply_chain_profile.py and were built
offline with retained pinned inputs. Original ML/PG/Redis/orchestrator images
and volumes remain unchanged; the targeted worker has a separate image.
Previous API/web/adapter images are retained as rollback inputs. The private
records include a consistent PostgreSQL dump, original owner designs/validation,
old journal records and the original private compose configuration.

## Operator paths
From the original checkout:
- Existing profile: local-backups/portuguese-sandbox-20261112/profile
- New private records: local-backups/portuguese-chain-20261113
- Review checkout: local-backups/portuguese-portal
- Existing designer/password: existing profile credentials.json (never print).

Use the installed original-checkout .venv/Scripts/python.exe. No dependency
downloads, production, staging, provider or ledger activation is involved.
Set PT_SANDBOX_PROFILE and PT_SANDBOX_RECORDS to those absolute paths.
Set $cfg to the existing profile's compose.private.json.

## Reviewed update before dispatch
1. apply_chain_profile.py --profile $env:PT_SANDBOX_PROFILE --records $env:PT_SANDBOX_RECORDS
   verifies isolation/provider/resource guards, backs up private compose and
   updates only API/web/adapter plus read-only observer/operator roles. It starts
   nothing and refuses repeated application. It leaves the old worker untouched.
2. docker --context desktop-linux compose -f $cfg run --rm --no-deps --entrypoint python bootstrap /review/register_chain.py
   adds separate v0.2 services/contracts; it refuses to mutate existing IDs.
3. docker --context desktop-linux compose -f $cfg up -d --no-build --pull never model-observer pt-adapter api web
   leaves database, Redis, original ML API, orchestrator and all other profiles
   intact. Check login, genuine capability versions/I/O digests, old results,
   owner-design preservation and provider disconnection.
4. python deploy/portuguese_sandbox/chain_review.py prepare
   creates only one separate correctly bound saved review copy through the
   normal authorized application routes. It never modifies the owner failure.
5. Inspect in Builder, edit/save/reload settings without executing, then restore
   the approved epochs 2 / batch size 4 / count 10 and required model_ref binding.

## Single authorized combined attempt
Publish source/tests/configuration before these explicit steps:
1. chain_review.py snapshot freezes exact final design, normal compile/readiness,
   root dataset reference, contract pins, current component/image/resource
   identities and queue state. It writes the new authorization policy.
2. chain_review.py authorize invokes the supported journal create operator.
   No legacy limit, record, model reference or checkpoint is reset or increased.
3. chain_review.py submit sends exactly one normal application workflow request,
   records the response and binds the authorization to that workflow once.
   Its pre-dispatch marker survives any unknown response. Never retry.
4. chain_review.py start_worker starts a separate one-shot worker_cli container
   for that exact workflow only. The daemon stays stopped. No owner-created or
   other workflow queue is processed.
5. chain_review.py observe reads only owned status/tasks/immutable submission
   and authenticated artifact evidence. Stop on failed/uncertain outcome; do not
   repair a response, reuse a model or send another workflow.
6. After both tasks complete and all proof validates, chain_review.py close
   requires the targeted worker stopped and queues empty, then closes the new
   scope through the supported operator. Retain its journal/audit/events/logs.

On failure: keep the consumed submission/worker markers and actual records.
Gracefully stop only the targeted worker if needed, use the journal operator to
close the new scope without claiming success, and report the exact failure.
No replacement grant, second submission or execution retry is authorized.

## Historical browser review / shutdown
The final report supplies the saved combined Builder and results URLs. Browser
review is read-only and requires no new execution or helper. The evidence reader
uses only read-only journal/model/output mounts, validates signed versioned
records and current hashes, and does not contact a live runtime to make claims.

For ordinary restart, start only retained postgres/redis first, wait for
pg_isready, then start ml/orchestrator/pt-adapter/api/web/model-observer as needed.
Never start worker or chain-worker for review. New scope must remain closed.
Shutdown: docker --context desktop-linux compose -f $cfg stop
Never down -v, rerun bootstrap, remove volumes, reset the journal or touch ledgers.
The one-shot worker container/logs are retained, not recreated for inspection.

Rollback stops this isolated profile's changed components, restores the private
compose backup and retained old API/web/adapter pins, then starts only safe
components with the same database/volumes. Additive registry versions and journal
history remain; do not restore an older database/journal over new evidence.
No PostgreSQL schema migration is required. The original Portuguese API is not
edited. Hosted multi-tenant authority, partner approval, scientific suitability
and production compatibility remain outside this local verification.
