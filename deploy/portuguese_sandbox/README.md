# Isolated Portuguese parameter sandbox

This profile uses actual retained Portuguese API bytes plus the experimental
parameter adapter; it is not the original deployment, a partner-approved contract
or a scientific qualification. Portal draft PR #22 stacks on PR #21; maintained
WP3 draft PR #4 stacks on PR #3.

## Pinned packaging
- Portal serving revision: 654b10754a7785fa3d650a4c543d3144b72b88df
- API image: sha256:974628a92ee14719396f4e19e0cca7a274c64e60cc09b7e37b3beabe9290da28
- Adapter source: be8722c01dc41b26b083302531e4a780bdec8598
- Adapter image: sha256:76f7eea8d48eff6aeb3182dc755cd70d195899404c17785ce73a5766b0352bba
- Retained web: sha256:913b314cc09a974b7dddcc1a85bc889bda599694970aed80c7b7b758e68d8eeb
  source f1e49485e37e; BUILD_ID 6y7rN_AJRS7b9xNgfh1Ab. Existing generic Builder controls are reused.
- Original ML image: sha256:557246d79612eaa2106266d60cc6b36970634afebb659e371658cce6a1f1f61f
  (pt33-tef-integrated-synthetic-data:latest). Unchanged, separate model volume.
- Original sidecar image preserved, unused: sha256:f7202018956f326c6dc62d3b7b699776d32dcaed54bd4eae0653ebac63d5a2e8.
- Maintained WP3 runtime retained: sha256:edcac597f327dc817ff0c9b9c930dbf9b4cb62235d42f2ef1940845ca1820a21.
  Its manifest names historical source c6695d8444edb14b94111f16d8620c460880849b; verify relevant source bytes against PR #3, rather than relabeling it.
- PostgreSQL and Redis IDs are pinned in profile.py. No dependencies downloaded.

The first adapter packaging attempt used a bare image ID in FROM. BuildKit treated
it as a repository name and rejected resolution; no image was pulled. The
Dockerfile now uses the existing local tag, whose full ID was verified before
building. Existing image tags were not overwritten.

## Preparation (operator only)
Use the existing host Python. Private directory below is outside Git:
local-backups/portuguese-sandbox-20261112/profile.
Run profile.py --directory that-path --adapter the-full-adapter-ID above once.
It refuses to overwrite an existing profile. It generates a new designer, control
token, database credentials, synthetic CSV and private compose configuration.
Do not print or publish compose.private.json, credentials.json or control.token.

New project: ai-effect-pt-parameters. Web 127.0.0.1:23124, API 127.0.0.1:28188.
All execution/data components join only an internal Docker network. The web has
a separate browser network; published ports are loopback only. No original volume
or ledger is mounted. Provider disabled; no provider secret or grant.

With $cfg pointing to compose.private.json:
1. docker --context desktop-linux compose -f $cfg up -d --no-build --pull never postgres redis
2. Wait for pg_isready; verify fresh isolated DB, empty models and Redis.
3. docker --context desktop-linux compose -f $cfg run --rm --no-deps initialize
4. docker --context desktop-linux compose -f $cfg run --rm --no-deps bootstrap
5. docker --context desktop-linux compose -f $cfg up -d --no-build --pull never orchestrator ml pt-adapter api web
6. Verify schemas, capabilities, source digests, auth, saved configuration and
   exact snapshots. Start only this project's worker after checking its queue.
   Never start another retained worker.

No command above submits a workflow. Before each explicit normal application
submission, persist its exact saved design, compile result, dataset/model SHA,
resource limits and remaining job counts. At most one necessary training and two
GenerateData submissions. Stop on failed or uncertain dispatch; never retry.

## Resources and semantics
ML: CPU 2, RAM 3 GiB, /tmp maximum 512 MiB, two numerical threads.
Other per-component limits total about 3 GiB, plus PostgreSQL/Redis disk.
400 synthetic rows, 2 numeric features, 100 observations/sequence = 4 training
sequences. Proposed sole training: epochs 1, batch size 4 (effective min(4,4)=4).
CSV generation 10/20 sequences should contain 1000/2000 data rows. These small
resource bounds do not establish model quality or scientific suitability.
Available memory was about 13 GiB and C: 19 GiB before profile activation;
incremental source layers/models estimated under 1 GiB. No large pulls.

Sign in at http://127.0.0.1:23124/login with the fresh designer recorded privately
in credentials.json. Generic Builder is authoritative for settings/Save/reload;
normal compile and immutable submission routes are authoritative for execution.
No recommendation/chat is prepared or sent.

Shutdown without deleting evidence:
docker --context desktop-linux compose -f $cfg stop
Restart only recorded appropriate components with compose start; do not rerun
bootstrap/initialize and do not start a worker with unresolved work.
Never use down -v. Rollback is simply stopping this separate project; previous
profiles/images/ports remain retained and unchanged.

## Remaining boundaries
ApplyFunction, sequence length, output format, arbitrary user/model paths,
overwrite and arbitrary kwargs remain unavailable. Ownership is an isolated
single-principal server-derived namespace, not a hosted multitenant solution.
Hosted testing needs service-owner/API approval, private auth/storage/network
design, pinned portable artifacts and a separate bounded execution plan.
Execution evidence will be appended only after actual outcomes.
