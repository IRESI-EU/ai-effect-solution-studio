# Local pilot and release review

Baseline: [PR #19 at 94c28277](https://github.com/IRESI-EU/ai-effect-solution-studio/tree/94c28277a60cc18d3e2095455844cde36afae463).
This milestone prepares supervised sessions for two or three first-time users on
http://127.0.0.1:23121/design-ai. It is not a production release.

## Evidence and component review

| Evidence / boundary | Review |
|---|---|
| Platform-controlled parameter delivery | [PR #18](https://github.com/IRESI-EU/ai-effect-solution-studio/pull/18), [two completed runs and protected artifacts](PARAMETERISATION_PLATFORM_VERIFICATION_2026-11-12.md). No repeat execution. |
| Genuine interpretation and composition controls | [PR #19](https://github.com/IRESI-EU/ai-effect-solution-studio/pull/19), [actual A/B responses and accounting](LOCAL_COMPOSITION_ACCEPTANCE_2026-11-12.md). No repeat model calls. |
| Verified production API baseline | 89072340c9a13f3aa49d3e433380de8928cc16dd. Use apps/api and relevant deploy paths in the cumulative comparison; current image/source recorded after packaging below. |
| Verified production web baseline | df5b75873326ab56cad608990f3bd4add125bcc4. Use apps/web and its dependency/build paths in the cumulative comparison. This is the actual server baseline, not historic Vercel metadata. |
| Authentication and reviewer boundary | Existing session authentication/RBAC and ownership checks remain authoritative. Restricted routes require an exact existing active reviewer ID; no admin bypass. Local pilot additionally requires the qualified local profile, one configured reviewer and shared accounting. Participants share a supervised private session for aie37-designer; no new accounts or multi-user acceptance claim. |
| Contract boundary | Only the existing local pair and unchanged active contract pins qualify for design composition. Actual template policy remains in place. New compositions are design-only; the registered local experiment has no execution grant. |
| Partner and licensing | [Source-backed contract dossier](contracts/dutch-production/README.md), [unconfirmed partner patch](partner-review/dutch-parameters/README.md), and [platform proof licensing limits](PARAMETERISATION_PLATFORM_VERIFICATION_2026-11-12.md). Partner baseline has no license file; local reuse does not establish redistribution permission. Partner-native output association, approved family/contracts and production qualification remain outside this pilot. |
| Artifact ownership | Candidate generic preview requires authorized workflow/submission/task association and integrity checks; unknown associations and unqualified transports stay denied. Existing capture downloads are a separate guarded historical path. Review cumulative ownership/onboarding and deployment-claim changes. |
| Accounting | One canonical Windows ledger; exact environment/consumer and single-reviewer API binding. Original USD0.10 ceiling, ten permits / USD0.050 lifetime reservations, fixed USD0.005 each. One unresolved permit blocks dispatch; unknown usage stays held, no retries/refund/fallback or copied allowance. Container-to-host verified private TLS, loopback authority and Windows host availability are operational dependencies. See [accounting runbook](../deploy/restricted-beta/ACCOUNTING.md). |
| Migrations | Additive 003_design_ai_pilot.sql, 004_instance_submissions.sql and 005_local_capture_records.sql above production. No new application migration in this milestone. Existing synthetic migration/restore and consistent production backup rehearsal remain in [the engineering review](DESIGN_AI_BETA_ENGINEERING_2026-11-11.md); no production DB access or migration is required for local preparation. |
| Local backup / rollback | Existing retained component images/builds and consistent private pre-update database dumps remain. New source-only API/web packages use pinned offline inputs; no data volume is replaced. Code rollback must never restore an old database over new writes or replace/revert the canonical ledger. Disable the provider before any rollback. |

## Narrow preparation changes

New conversation creates a unique normal-route conversation URL and remounts the
workspace with a separate browser storage key. Previous discovery, accepted
draft/conversation and server-side saved work remain. It makes no API/model
request or draft. It requires no hidden bootstrap page, alternate hostname,
account or synthetic profile. Operators may bookmark a conversation URL to
return to its browser-local history; saved drafts remain available in Resume.

The server supplies an explicit restricted local design-only notice. This flag
does not authorize a provider request or execution. Offline checks cover fresh
conversation isolation, named-reviewer guards, missing accounting/transport,
exhausted limits and composed execution denial. No paid smoke request is allowed.

## Participant and observer handoff

- [Participant brief](LOCAL_PILOT_PARTICIPANT_BRIEF_2026-11-12.md)
- [Blank observer template](LOCAL_PILOT_OBSERVER_TEMPLATE_2026-11-12.md)

Prepare one fresh normal conversation for each person using New conversation,
keeping previous URLs/history. Initially suggest two Sends per participant.
Further clarification still uses the same ten-call scope; no automatic retry.
Do not record agent preparation as human observations. Completed observations
belong only in the private local record, not this repository.

## Production release decisions remain separate

- Cumulative draft-stack code review and required checks/attribution; no merge
  or self-approval. Vercel author/access failures remain distinct from code.
- Normal production sign-in and exact existing production reviewer identity.
  Do not retry/reset the earlier failed temporary credential or invent reviewers.
- Responsible Dutch owner selection, contract/version/protocol confirmation,
  licensing permission and task-specific output-association engineering for
  partner-native runtime use. Local platform-controlled proof is not that approval.
- Hosted authority/storage/transport durability, private networking, secret
  management and operational ownership. Do not silently choose an architecture.
- Production schema inventory, migration/backup/restore/rollback plan and actual
  environment compatibility. No production deployment or new composed execution.

## Activation record

Preparation checkpoint only: focused checks and packaging are recorded next.
No pilot amendment or paid request has occurred at this source checkpoint.
Human observations remain blank.
