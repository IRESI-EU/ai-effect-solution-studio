# December 2026 production release: plan and runbook

Status: **draft for approval.** Target window: **Wednesday 9 December 2026, 10:00 CET** (about 30 minutes, the
Studio is unavailable for about one minute). Buffer until the 18 December milestone.

This release brings production (`platform.ai-effect.eu`) up to `main`: service settings, Design with AI,
saved run outputs and gRPC previews, the new design system, and the composer-style Builder (PR #31).
It follows the general rules in [PRODUCTION_RUNBOOK.md](PRODUCTION_RUNBOOK.md).

## What is running today (checked 26 Nov 2026)

| Part | Production now | After this release |
| --- | --- | --- |
| Studio web | `df5b758` (release folder `~/ai-effect-solution-studio-release-df5b758`) | `main` at release time |
| Studio API | `8907234` (release folder `~/ai-effect-solution-studio-release-8907234`) | same commit as web |
| Studio database | Postgres 16, compose project `ai-effect-solution-studio`, started from `~/ai-effect-solution-studio-staging` | **unchanged** (not recreated) |
| Orchestrator | WP3 `486ccc7` in `~/ai-effect-wp3/orchestrator` (running code matches this commit exactly) | WP3 `main` (`bfe655d`) |
| Node services | containers on `ai-effect-services` | **unchanged** |

Findings that shape the plan:

- **Nothing on production is missing from `main`.** Both production commits are ancestors of `main`;
  `main` adds 36 commits on top. Deploying `main` loses no live behaviour.
- **No manual database migration.** The release only adds two tables (`run_output_snapshots`,
  `design_ai_usage`), which the API creates at start-up. No existing table changes. Staging has run
  this code on a copy of the production database since 24 Nov.
- **Production settings live in `~/ai-effect-solution-studio-staging/.env.production`.** The folder name is
  misleading (it is production). Every Studio command below passes this file explicitly.
- **The orchestrator change is backwards compatible.** It adds optional per-step `parameters` and start
  inputs; requests without them behave exactly as today, and existing Redis state still loads.
  Upgrading it first means the old Studio keeps working while the new one is deployed.
- **The server's orchestrator checkout has a local security edit** in `orchestrator/docker-compose.yml`
  (Redis not published, API bound to `127.0.0.1`). It must be kept. The server cannot `git pull`
  (no deploy key), so the code change is applied as a patch.
- Production data: 31 users, 38 catalogue services, 60 solutions, 74 runs (last on 24 Nov).
  Disk: 76 GB free. Nightly database backups run at 02:45.

## Before the window

1. **Merge PR #31** (it contains #28 and #30) so the deployed commit is on `main`. Note the commit: `REL`.
2. **Staging = `REL`.** Staging already runs the same code; leave it there and re-test for a few days.
3. **Design with AI on production:** create a separate OpenAI key with a monthly spending limit, decide the
   daily limit per user (staging: 40), and keep the key only in the production environment file.
4. **Tell partners** about the window (Studio briefly unavailable; runs should not be started during it).
5. **Prepare** on the server, without touching anything running:
   - upload the `REL` source to `~/ai-effect-solution-studio-release-REL`;
   - upload the orchestrator patch (`git diff 486ccc7 bfe655d -- orchestrator/src`) to `~/wp3-486ccc7-to-bfe655d.patch`
     and check it applies: `git -C ~/ai-effect-wp3 apply --check ~/wp3-486ccc7-to-bfe655d.patch`;
   - pre-build the new images (no restart): see step 2 and 3 commands with `build` only.

## During the window

### Step 1: freeze and back up (5 min)

```bash
# no workflow may be running
docker exec orchestrator-redis-1 sh -c 'redis-cli --scan --pattern "workflow:wf-*"' | grep -v ':tasks$' \
  | xargs -r -n1 docker exec orchestrator-redis-1 redis-cli get | grep -c '"running"'   # must print 0

# database and uploaded contracts
docker exec ai-effect-solution-studio-postgres-1 sh -c 'pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB"' \
  > ~/ai-effect-backups/solution-studio/pre-release-REL.dump
docker run --rm -v ai-effect-solution-studio_service_contracts:/c:ro -v ~/ai-effect-backups:/b alpine \
  tar czf /b/service-contracts-pre-release-REL.tgz -C /c .

# keep the current orchestrator images for rollback
docker tag orchestrator-api:latest orchestrator-api:486ccc7
docker tag orchestrator-worker:latest orchestrator-worker:486ccc7
```

### Step 2: orchestrator (5 min)

```bash
cd ~/ai-effect-wp3
git apply ~/wp3-486ccc7-to-bfe655d.patch          # local docker-compose.yml edit is untouched
cd orchestrator
docker compose build api worker
docker compose up -d --no-deps api worker         # Redis is not recreated
curl -fsS http://127.0.0.1:18000/health
```

The old Studio still works against the new orchestrator. Run one existing solution (e.g. the German
time-series demo) from the old Studio before continuing.

### Step 3: Studio (5 min, about one minute unavailable)

```bash
cd ~/ai-effect-solution-studio-release-REL
export STUDIO_IMAGE_TAG=REL
docker compose -p ai-effect-solution-studio \
  -f docker-compose.prod.yml -f docker-compose.traefik.yml \
  --env-file ~/ai-effect-solution-studio-staging/.env.production build api web
docker compose -p ai-effect-solution-studio \
  -f docker-compose.prod.yml -f docker-compose.traefik.yml \
  --env-file ~/ai-effect-solution-studio-staging/.env.production up -d --no-deps api web
```

`--no-deps api web` is essential: it leaves the database container alone.

### Step 4: catalogue data (10 min)

Run with a dry run first and review the output, then apply. Both scripts were used on staging.

1. `catalogue_cleanup.py`: moves solutions off duplicate catalogue entries, then archives 11
   duplicates and test entries. On staging it moved 9 solutions.
2. `declare_settings.py`: declares the settings the Dutch grid synthesiser, Danish configuration
   assistant and Portuguese data loader already read.

### Step 5: Design with AI (2 min)

Add `DESIGN_AI_ENABLED=true`, `DESIGN_AI_PROVIDER=openai`, `DESIGN_AI_API_KEY=…` and
`DESIGN_AI_DAILY_REQUESTS_PER_USER=40` to the production environment file, then repeat the
`up -d --no-deps api` command. Leave it off if the key is not ready; everything else works without it.

### Step 6: checks (10 min)

| Check | Expected |
| --- | --- |
| `https://platform.ai-effect.eu` without signing in | Dashboard and public catalogue load; TLS valid |
| Sign in as admin and as a partner account | Correct menus for each role |
| Solutions | All 60 solutions listed; an older one opens on the canvas without overlapping cards |
| Runs | Run history visible, including runs from before the release |
| Builder: German time-series example in Design with AI | Workflow on canvas, decimals setting filled in |
| Run tab: Check design, Check services, Deploy now | Run completes; results and preview shown |
| Dutch benchmark and Danish topology solutions | Both run; Danish drawings preview |
| Settings | Changing the Dutch seed changes the result |

## Rollback (about 5 minutes each, independent)

- **Studio:** start the previous containers again from their release folders, for example
  `cd ~/ai-effect-solution-studio-release-df5b758 && STUDIO_IMAGE_TAG=df5b758 docker compose -p ai-effect-solution-studio -f docker-compose.prod.yml -f docker-compose.traefik.yml --env-file ~/ai-effect-solution-studio-staging/.env.production up -d --no-deps web`,
  and the same for `api` from the `8907234` folder. The old code ignores the two new tables, so no
  database restore is needed.
- **Catalogue data:** only if the clean-up itself is wrong, restore `pre-release-REL.dump`
  (this also undoes anything partners saved after the release).
- **Orchestrator:** `git -C ~/ai-effect-wp3 apply -R ~/wp3-486ccc7-to-bfe655d.patch`, retag the
  `:486ccc7` images as `:latest`, and `docker compose up -d --no-deps api worker`.

Keep the old release folders, images and backups until the release has been stable for two weeks.

## Known issues not changed by this release

- Two node containers share the network alias `synthetic-data` (Portuguese and Dutch); calls to that
  alias can reach the wrong service. Needs the node owners.
- The Portuguese pipeline needs a dataset mounted in its data loader before it can run.
- Orchestrator reliability items (lost tasks when a worker restarts, no time limits) are tracked
  separately and are not part of this release.

## After the release

- Move the production environment file to a clearly named folder (for example `~/ai-effect-production/`).
- Update [ROADMAP.md](ROADMAP.md) and [CURRENT_CAPABILITIES.md](CURRENT_CAPABILITIES.md).
