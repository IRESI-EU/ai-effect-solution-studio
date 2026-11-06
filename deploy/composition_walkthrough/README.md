# Host offline controls walkthrough

**Offline controls walkthrough: prepared synthetic proposal. No live AI or execution.**

This opt-in harness runs the existing PR #15 application, not a substitute UI.
It needs only installed Python/Node dependencies. SQLite JSONB compilation is
confined to the harness, using the portable test-suite technique; production
database behavior is unchanged. It imports no historical demonstration database,
source template, account, evidence, grant or ledger.

## Prepared local entry

Open **http://127.0.0.1:23123/api/offline-controls/human**. Sign in normally as
`controls-human@example.test`, using only the `human.password` value in the private
`local-backups/composition-browser-acceptance-20261106/profile/private-credentials.json`
under the original portal checkout. Do not paste the password into reports,
screenshots, logs or Git. The existing browser may already be signed into that
dedicated account. The entry redirects to the actual `/design-ai` page, restoring
only its existing owner-bound recommendation/conversation format.

Two recommendations were prepared through normal authenticated discovery routes
and a strictly bounded, labelled provider double. The agent recommendation was
created and checked separately. The human recommendation has a separate nonce
and account, no draft or saved design, and remains uncreated for the participant.
Reopening the entry does not regenerate its nonce or reset any engineering state.

## Participant brief — five steps

1. Read the label and proposal. Explain the two steps, count 3, what passes between them, and what has not been checked. Scroll within the proposal card as needed; no chat message is required.
2. Choose **Create this experiment**, then **Apply changes**. Explain what is now in the draft and whether anything executed.
3. Choose **Undo**. Confirm the applied design is empty and the same reviewable proposal is available. Choose **Apply changes** again directly; no helper or operator action is needed.
4. Choose **Save draft**, reload, then **Open in Build Solution**. Review count 3 and the saved connection. Technical details contain the two contract pins and instance IDs.
5. Explain whether AI or a workflow executed and what remains unverified. Stop; no chat, readiness, deployment or execution acceptance is part of this walkthrough.

## Observer record — awaiting human walkthrough

Participant/date: ______  Observer: ______

| Step | Completion | Hesitation | Confusing wording | Assistance |
|---|---|---|---|---|
| Review | | | | |
| Create/Apply | | | | |
| Undo/Apply again | | | | |
| Save/reload/Builder | | | | |
| Explain execution boundary | | | | |

These fields are intentionally blank. Agent checks are technical acceptance
evidence, not owner or independent participant observations. Real-provider
interpretation, the complete first-time journey, PostgreSQL concurrency, runtime
qualification, scientific validity and production compatibility remain unverified.

## Operator configuration and safeguards

- API: `127.0.0.1:28187`, native Uvicorn; web: `127.0.0.1:23123`, native Next dev
  with installed Webpack. Both bind IPv4 loopback only. HTTP uses the isolated
  profile's existing local-cookie behavior; this is no HTTPS/production claim.
- Web uses `.next-controls-20261106`, preserving the retained `.next` build.
  The launcher snapshots/restores only verified Next-generated type-reference
  adjustments. No dependencies, containers or images are downloaded or built.
- API reads only `profile/walkthrough.sqlite3`. New isolated designer accounts
  and two synthetic catalogue operations/contracts are created once. There is
  no saved workflow template, execution history, actual grid or algorithm output.
- Authenticated Create/Apply/Undo/Save, compatibility/compiler checks, complete
  authority snapshots, source kind, ownership and revision protections are the
  normal application code. The entry page supplies no duplicate control UI.
- The fixture responds only during explicit one-time preparation to one exact
  synthetic prompt and the one validated pair. Normal serving disables chat
  server-side and reports no connected real provider. No production fallback is
  introduced. Provider SDK construction/respond calls, outbound TCP connections,
  readiness/runtime calls and HTTP execution/submission routes are denied. The
  stdlib Windows asyncio wake-up socketpair is the sole connect exception.
- No allowance or grant is attached. Historical provider/grants remain disabled
  and their protected hashes/ledger stay unchanged at 13/13.
- Startup PIDs and API/web logs are private in the dated acceptance folder. Do
  not run the launcher when either port is occupied or reset/re-prepare this
  profile. Leave both native processes running for the walkthrough.

For an explicitly authorized fresh installation only:

```powershell
$profile = '<new absolute disposable profile directory>'
& ../../.venv/Scripts/python.exe deploy/composition_walkthrough/harness.py prepare --profile $profile
& deploy/composition_walkthrough/Start-Walkthrough.ps1 -Profile $profile
```

From the review worktree, if these specific processes later stop, use the **same**
retained profile path with `Start-Walkthrough.ps1`; never run `prepare` again.
The launcher refuses occupied ports and performs a bounded readiness check. A
failure means inspect its private logs, not repeat startup or repair Docker.

`inspect_controls.py` is an agent evidence/rejection checker, not part of the
participant flow. Its valid Create/Apply/Undo/Save actions happen in the browser.
`test_safety.py` exercises outbound denials without reaching a network.
