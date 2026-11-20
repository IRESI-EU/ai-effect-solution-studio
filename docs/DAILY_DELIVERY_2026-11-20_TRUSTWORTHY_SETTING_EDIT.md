# Delivery checkpoint — one trustworthy setting edit — 20 November 2026

**Demonstrated in the local browser, using explicitly scripted offline model-response replay.** A pending maximum changed from4 to2, its factual review matched the candidate, explicit Apply-and-save persisted it, and reopening the same solution retained2. This establishes the application-side edit/review/persistence path for these fixtures. It does not establish real-model interpretation or general conversational reliability.

Serving source: **`a63697ea5371b59ed23796715357bdb97883f258`**, isolated branch `codex/trustworthy-setting-edit-20261120`, based on published `13e575f0d79c30235aa93e6bca556a64fada2e78`. Later commits contain documentation and evidence only. No WP3 changes, dependency installation, production deployment or merge.

[Observed browser/source evidence](verification/trustworthy-setting-edit-20261120.json) · [Review screenshot](verification/trustworthy-setting-review-final-20261120.png) · [Reopened Builder screenshot](verification/trustworthy-setting-reopened-final-20261120.png).

## Previous failure and reproduction

The actual19November J2 evidence is available: [original failed journey](COMPLETE_GENUINE_JOURNEY_2026-11-19.md) and [exact rejected response fixture](../apps/api/tests/fixtures/complete-journey-rejected-j2-20261119.json). Fixture SHA-256 remains `174512a02f45808eb4f54cb53117058af88ae3c4959b89901d0b006c543979a8`.

Observed facts: the previous model received the correct pending proposal with maximum4. It returned `outcome=proposal`, no edits, and prose claiming that the existing maximum satisfied the request for2. SDK/Pydantic validation rejected it. No candidate construction, conversation reply or Apply/Run followed. This pass reproduced that rejection offline before modifying code; the original output remains rejected after the correction. It was not repaired into an invented successful response.

The model had been asked both to propose low-level edits and write a change explanation. The application already knew the actual saved/pending base, approved settings, values, target references and candidate difference. The provider input/output qualification from the previous pass did not test this conversational responsibility split and is not cited as proof that chat interpretation works.

## Small responsibility split

For a setting-only request the model contract now offers `outcome=setting_edit`, an explicit current saved/pending base, and one `parameter_action`: operation `set_parameters`, scoped `target_ref`, and requested name/value pairs. The four supported scalar types come from the existing parameter core. The model's message must be null for this action; it supplies no factual change summary, assumptions, structural edits or execution authority. Missing/empty actions, duplicate names, conflicting contents and nonfinite/unsupported types are rejected. The actual SDK strict schema/parse/accounting checks use offline mocked HTTP, not paid calls.

Application code resolves the target against the declared actual workflow base and current approved contract. It adapts the action into the existing candidate editor and uses the same typed parameter validation and canonical writer as Builder. It merges only requested overrides, calculates actual effective before/after values, and writes an application-generated change summary. The UI labels and renders that summary as plain text. Legacy setting-only responses also receive an application summary; misleading provider prose is not used as the edit explanation.

The summary says **proposed** before Apply. Its structured `change_summary` records application source, saved/pending base, status and actual changed values. After the owned normal writer succeeds, the UI may show the application-confirmed applied-and-saved notice. Run remains separate. An already-satisfied validated action gets a factual no-change reply, no redundant candidate and no saved-graph mutation.

A setting action cannot silently choose the saved base while an earlier pending review exists. Pending edits replay cumulatively against the original saved base, retaining earlier additions, labels/settings, connections, assumptions history and stable instance IDs. Current scoped references, catalogue authority, ownership, optimistic revisions, parameter limits and explicit Apply remain required. Invalid or stale actions preserve the previous review/messages/saved content. No user-word regex, exact4-to2 parser, node/service-ID branch, automatic user-intent repair or weaker validator was added. Broader structural/explanatory conversation behaviour was not rewritten.

[Official structured-output guidance](https://developers.openai.com/api/docs/guides/structured-outputs) was checked for the strict required/nullable schema contract; application business validation remains necessary. No API key was loaded and no provider connectivity probe was made.

## Focused verification

| Check | Result and scope |
| --- | --- |
| Original J2 output before modification | Offline schema rejection reproduced; historical evidence unchanged. |
| Correct supplied4→2 action and differently worded request | Actual pending diff4→2, candidate2, same previous pending title/additions and unrelated settings; this supplies the interpretation and does not test NLP. |
| Saved base and already-satisfied requests | Accurate no-change result for the actual current value; exact pending review or saved graph retained. |
| Empty/missing/duplicate/invalid/ambiguous actions | Rejected without success message or state mutation. Ambiguous labels/raw IDs cannot replace scoped references. |
| Stale base/revision/hash/manual Save | Rejected; no stale Apply. |
| Applied/saved consistency | Complete persisted graph equals the reviewed candidate hash; normal Save/reopen retains values, other instances, connections and input. |
| Affected backend suite | **82 passed**, zero skips. |
| Existing assistant/provider/accounting compatibility | **28 passed**, zero skips, offline doubles and disposable synthetic ledgers only. |
| Actual assistant component checks | **6 passed**; plain factual summary, explicit Apply navigation and separation from Run. |
| Next production build / actual endpoint health | PASS; starter READY; browser login and API health verified. |

An early test compared the API's display-hydrated legacy nodes with raw stored candidate bytes. Diagnosis showed read-only catalogue metadata hydration, not a parameter-persistence defect. The final check compares the complete actual stored graph with the reviewed hash, then verifies the normal reopened API/UI values separately. Earlier fixture failures also exposed outdated offline fixtures which selected the saved base despite an existing pending rename; those supplied test responses now bind to the real pending base. The application guard was retained. No failure was hidden by weakening schema, ownership, hash or parameter assertions.

## Actual browser walkthrough

The fresh host-only workspace serves UI **http://127.0.0.1:23135**, API **http://127.0.0.1:28269/health**. It uses a new private database copy of the verified offline fixture environment, its own cookie and outputs location, the real application code and normal sign-in/owned solution routes. It starts no Docker/Redis/worker/ML stack; provider keys/model configuration and allowance files are empty. Submission routes are blocked in this harness. Header and assistant explicitly say offline/scripted/no model. All96 copied API files match serving source.

1. Sign in as the ordinary fixture designer; start a fresh normal saved solution through Design with AI.
2. Send the documented offline setup response. It proposes the actual approved fixture Generator and Drawing A connection, maximum4, heat exchangers true (published default), bypasses false (deliberate unrelated override). Do not Apply yet.
3. Send “Please cap the proposed layouts at two instead, leaving the other settings and connection alone.” The supplied interpretation contains only the pending scoped parameter action for2. The application displays **Maximum candidate layouts4→2**, full candidate2, unchanged false bypass and the same connection/instances. Saved graph remains unchanged before Apply.
4. Click **Apply and save reviewed changes**. This is the product's combined explicit Apply/Save control; no additional Save is shown for a clean already-saved design. The stored whole-design hash equals the reviewed candidate: `5b5e0d26f9b8dd8e70519e641e0746acce30c28dd2ffa3a2fe14eaecc2c9f391`.
5. Leave through Solutions and reopen this same listed solution in Builder. Select Generator: maximum2, bypasses false, heat exchangers true; same Drawing A connection and conversation. The reopened stored graph and complete owned solution response equal the post-Apply snapshot.
6. Send the documented saved-value check. The supplied action requests the already-saved2. Application says no change is needed, creates no proposal and preserves the graph. Its wording is scoped to this request: “This request made no design changes and did not run the workflow.” It does not contradict the earlier successful Apply.

Current saved example: [open Builder](http://127.0.0.1:23135/builder?solutionId=438d2a04-8040-41e1-9133-22688ba7d1d1). The three scripted replay messages are documented in `deploy/setting_edit_walkthrough/offline_provider.py`; this completed example is ready to inspect, not an open-ended offline interpreter. The three exact fixture messages may be repeated in a new empty saved solution; the replay cursor is scoped to that solution. Replay responses are explicitly fixtures, not reconstructed genuine responses. The old failed solution at23134 is untouched.

## Preservation and remaining uncertainty

**Paid calls0; new spending scopes/ledgers0; designer workflow Runs0.** Four old closed ledgers remain byte-identical. Original checkout remains `12aae82dd47b078ba077aca40b0712c375b9d7f3` with150 dirty entries. Retained23124 demo, guarded23125 review and23134 failed genuine checkpoint remain healthy. Historical J2 bytes, saved designs/results, old model/state/evidence volumes and spending closures were not altered. No production access/change, paid service or message to another person occurred.

Wire schema SHA-256: `be5c2f476b825e4ddf105d654f17f65b49b70a442354a7d1ad6eb62bdd09ba93`; prompt SHA-256: `3e5c65e3dc25e7d7149fe0cc5e4e55a9dc4bed9e53069af4a2fec1b52d7291d8`.

The application path now has a demonstrated small outcome with a supplied correct action. **The real model has not been retested:** it could still select the wrong target/value/outcome. Offline paraphrase cases do not establish reliable interpretation. Next specific problem: determine whether genuine interpretation reliably emits the small scoped action for numerical changes, paraphrases and ambiguous targets, using a separately approved bounded acceptance after reviewing this frozen correction. Do not advance automatically to the complete journey, new nodes, execution or release. This pass grants no future paid authority.

## Publication

The isolated development branch is published without merging or force-pushing. The final evidence commit is the branch tip; serving source remains the exact implementation commit above. Credentials, operator snapshots, database copies, process/build logs and closed-ledger files stay in ignored local storage. Preliminary screenshots are retained as dated initial offline evidence; the linked final screenshots match the serving source.
