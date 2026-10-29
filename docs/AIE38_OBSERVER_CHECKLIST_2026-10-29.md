# AIE-38 observer and operator checklist — 29 October 2026

**Status: prepared; awaiting human walkthrough.** Participant, task outcomes,
hesitations, quotes and assistance observations are **not recorded**. Automated
checks and the agent's preparation are not participant observations. Do not mark
tasks complete from the earlier automated Apply/Undo evidence.

Use [the participant brief](AIE38_PARTICIPANT_BRIEF_2026-10-29.md) without showing
the observer answer criteria below first. Record a participant code, prior use
of this interface, relationship to the implementation, observer, date and browser
when a person is actually available. Do not call an implementer demonstration an
independent participant result. Do not contact or recruit anyone automatically.

## Short operator checklist

1. Use the existing **23122 web / 28186 offline API** processes and existing
   PostgreSQL cluster. Do not initialize/reset a profile or build another stack.
   The source remains PR #11's existing implementation; no terminology changes.
2. Read sign-in details privately from the existing local credential file:
   `local-backups/aie38-profile-20261028/private-config.json`, relative to the
   original production-ui checkout. Login identifier: `aie38-offline@example.test`.
   Never print/copy its password into notes, logs, screenshots or the report.
   No credentials, permissions or profiles need changing.
3. Sign in at <http://localhost:23122/login>, then open the exact
   [prepared draft](http://localhost:23122/design-ai?draftId=fe8110e0-631d-4527-aedc-2979e44ed83b).
   Sign-in drops the draft query, so reopen that exact link afterwards.
   Confirm **OFFLINE TEST FIXTURE**, draft prefix `fe8110e0`, revision **0**,
   **Proposed changes**, enabled **Apply changes** and disabled **Undo**.
   Confirm no saved solution exists for this draft. Do not Apply before the person.
4. Give the participant the brief and record their explanations before helping.
   Do not require free-form chat: this fixture cannot interpret arbitrary messages.
5. After the person Applies and Undoes, pause the observation. From the original
   checkout root, run the prepared private operator helper once:

   ```powershell
   .venv/Scripts/python.exe local-backups/aie38-walkthrough-20261029/restore_prepared_proposal.py
   ```

   The helper requires this exact draft at revision **2**, the complete original
   design and no pending proposal. It checks the offline provider identity and
   explicit submission guard, then queues the existing fixture and sends only its
   exact known request through the normal application API. It never Applies,
   Saves or executes. It refuses unexpected state, an existing queue or a repeated
   recorded restoration. Preserve failures; do not reset or repair the draft.
   The helper is prepared but **has not been executed** against this participant copy.
6. Record this as **planned operator fixture assistance**, including who ran it
   and when. Ask the person to refresh and continue with Apply, Save and Builder.
   Record all additional help separately. Do not present this as a fully
   unassisted journey or treat the planned restore alone as a participant failure.
7. After Save, Builder's expected URL is
   <http://localhost:23122/builder?solutionId=2b58ac9e-6341-4b2b-88b3-d5607027c0d2>.
   It is a reserved identity, **not yet a saved solution**. Do not open it as a
   successful handoff before the person's Save. Do not select Prepare & deploy,
   Check readiness again or other execution controls.
8. Preserve this draft and receipts afterwards. Record actual findings in a new
   dated observation record; retain this unfilled preparation checklist. If no
   person is available, leave the status **prepared; awaiting human walkthrough**.

The optional narrow fixture is
<http://localhost:23122/api/offline-fixture/narrow?draft_id=fe8110e0-631d-4527-aedc-2979e44ed83b>.
It uses the same draft, not a second attempt. Choose one layout before starting;
do not pre-consume the draft in another layout. A narrow iframe is not a physical
device test. Original completed revision-3 copies remain separate and untouched.

## Observation record — unfilled

Participant code: **not recorded**. Observer: **not recorded**.
Date/time and layout: **not recorded**. Prior interface/implementation knowledge:
**not recorded**. No audio/video or identifying participant information is required.

For each task, record independent / assisted / not completed / not observed.
Default below is not observed, not a failure. Note the actual start/end or elapsed
time only if measured. For hesitation, note the location and behavior: a pause of
about five seconds, rereading, backtracking or an explicit uncertainty can be
logged; it is not automatically an error. Mark estimates as estimates.

| Task | Completion | Hesitation / confusing wording | Assistance / evidence |
|---|---|---|---|
| Explain changes, preserved data and connections before Apply | Not observed | Not recorded | Not recorded |
| Apply changes; explain resulting state | Not observed | Not recorded | Not recorded |
| Undo; explain restored state | Not observed | Not recorded | Not recorded |
| Planned fixture restoration and participant refresh | Not observed | Not recorded | Not performed; operator setup planned |
| Apply again; Save draft | Not observed | Not recorded | Not recorded |
| Open Builder; explain expected design | Not observed | Not recorded | Not recorded |
| Explain whether an experiment executed, with on-screen evidence | Not observed | Not recorded | Not recorded |

Assistance log (time, task, requested/offered, helper, exact prompt/action,
planned-fixture or unplanned, effect): **no entries**.

Verbatim participant wording concerns and context: **no entries**.
Observed completion summary: **not observed**.
Any stopping point/reason: **not recorded**.

## Observer criteria — do not coach with these before the explanation

The proposal adds RunBenchmark and a named captured_grid connection, removes the
generator-to-output edge and routes benchmark-to-output. Existing generator
identity, seed 42, contract pins, input and unrelated design data remain unchanged.
Pending review does not apply the edit. Apply changes the draft; Undo restores
the complete original graph. Save persists the applied graph, and Builder shows
that saved copy. None of these actions executes an experiment. Record the person's
actual understanding, omissions and evidence; do not replace their answer with
these criteria or adjust criteria after observing them.

## Wording concerns for later team discussion — not participant findings

These are preparation notes, not observations or agreed replacement terms:

- **Active experiment**, **Workflow preview**, **CURRENT DRAFT**, **Draft saved**
  and **Open in Build Solution** may be interpreted as different lifecycle states.
- The inherited workflow-output label **Recorded benchmark** could suggest a
  recorded result even though this copy has not executed.
- **Design checks complete** must be read alongside **runtime unchecked**; ask
  whether the distinction is understood without supplying the answer first.
- Because the operator prepared the proposal through the normal API, this browser
  has no retained conversation; its existing message says earlier conversation
  was not retained. Record any confusion rather than inventing chat history.
- **Save draft** is enabled while a proposal is pending; record whether the person
  distinguishes the current design from a proposed change. Do not change this control
  or coach the distinction before their explanation.
- Undo clears the pending proposal. The planned fixture restore is a study setup
  dependency and should be recorded separately from spontaneous help.

Keep the existing workflow/run/session vocabulary unchanged in PR #11. Capture
actual participant wording and context for the team's later terminology decision;
do not add a lifecycle redesign to this bounded structural review.
