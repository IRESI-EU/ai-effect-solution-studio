# Offline structural composition profile

This harness is test infrastructure only. Normal application behavior always uses
the configured provider; it has no fixture/fallback switch. The harness overrides
the provider dependency with a single-use, explicitly queued structured response,
parsed by `AssistantTurn` and handled by the normal chat/MCP/proposal paths.

It reuses the existing qualification PostgreSQL cluster at loopback port 28145.
Preparation reads only the two qualified services/contracts and the saved design,
then creates one separate disposable database. It does not copy credentials,
accounts, execution history, artifact contents or spending records. It refuses an
existing directory or database. Never prepare again to reset the current profile.

From the review checkout, for an explicitly authorized fresh installation:

```powershell
python deploy/aie38/offline_profile.py prepare --profile <new-private-directory> --source-env <existing-aie37-private-api.env>
python deploy/aie38/offline_profile.py serve --profile <same-private-directory>
```

The local reviewer credential record is `<private-directory>/private-config.json`.
Read it privately; never print it, capture it in a screenshot or commit it. The
harness uses a distinct session-cookie name. Existing accounts and profiles remain
untouched. Only the required approved catalogue records are mirrored.

Build/start `apps/web` with `INTERNAL_API_URL=http://127.0.0.1:28186`, an explicit
OFFLINE environment label and an empty provider key. Use the installed Next
`build --webpack`, then `start -H 127.0.0.1 -p 23122`. Do not overwrite a running
frontend's build output. Sign in, choose **Compose a connected analyzer**, and use
its normal separate-copy action to obtain a revision-0 draft.

Queue a response against that exact draft:

```powershell
python deploy/aie38/offline_profile.py queue --profile <private-directory> --draft <draft-id> --case main
```

Send the exact main request in Design with AI:

> Add a benchmark step after the grid generator and use the grid it produces. Keep the generator settings unchanged.

The fixture checks the exact draft ID, revision, context and request. Consumption
removes the queued file; arbitrary messages have no response and never fall back
to a model. `--case ambiguous` queues a labelled clarification for “Add a benchmark
using the grid.” Neither fixture establishes provider intent quality.

The SDK/provider entry point raises if called. Middleware returns 403 for workflow
submission, runtime preflight, deployment and orchestrator routes. Only the pure
`/workflows/compile` route is permitted. An unreachable orchestrator address is an
additional configuration precaution, not the submission guard. Capture settings,
provider keys and allowance paths are cleared; the existing exhausted ledger is
neither opened for writing nor replaced. No new runtime containers are needed.

The test-only `/api/offline-fixture/narrow?draft_id=<draft-id>` page frames the real
application at 390 × 844 CSS pixels. It uses normal authentication, Apply, Undo,
Save and Builder, and is labelled as a responsive fixture. This is not a physical
device or independent usability test. Keep drafts, source records, boundary logs
and databases when stopping only these new API/frontend processes.

See [the AIE-38 report](../../docs/AIE38_CONVERSATIONAL_COMPOSITION.md) for the
existing review copies and measured evidence. No provider call or workflow run is
authorized by these instructions.
