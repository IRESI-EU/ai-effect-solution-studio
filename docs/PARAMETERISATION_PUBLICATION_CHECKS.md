# Review publication checks — 27 October 2026

These checks ran on the isolated source prepared for the review commits, not on
the preserved running application images. No paid provider request, real workflow
submission or new algorithm execution was used.

| Scope | Result and provenance |
|---|---|
| Foundation portable API | 51 passed; disposable SQLite and provider/HTTP fixtures |
| Foundation web utilities | 5 passed |
| Foundation typecheck/build | TypeScript passed; Next 16 production build passed with `--webpack` |
| Registry/compiler intermediate layer | 27 focused offline tests passed |
| Final portable API | 173 passed; 1,428 existing deprecation warnings, no skips |
| PostgreSQL registry/input | 65 passed; three warnings; new exclusive random local test database, removed after the run |
| Final web utilities | 22 passed; Node's existing typeless-module warning |
| Final typecheck/build | TypeScript passed; Next 16 production build passed with `--webpack` |
| WP3 maintained source | 317 unit tests passed, no exclusions; HTTP/fakeredis fixtures in existing pinned dependency image, network disabled |
| Validator provenance | Exact shared validator bytes/digest; LF attributes prevent Windows checkout drift |
| Secret scan | Gitleaks 8.30.1; staged diffs and new commit ranges, with redacted local reports |
| Diff review | Explicit allowlists and staged inspections; whitespace checks passed |

Commands, from the relevant checkout/workspace:

```text
PYTHONPATH=apps/api python -m pytest apps/api/tests -q
python -m pytest apps/api/app/tests/test_operation_contracts.py apps/api/app/tests/test_run_input_artifacts.py -q
node node_modules/typescript/bin/tsc --noEmit
node --test --test-isolation=none <all app/lib *.test.ts files>
node node_modules/next/dist/bin/next build --webpack
PYTHONPATH=orchestrator/src python -m pytest orchestrator/tests/unit -q
gitleaks git <checkout> --pre-commit --staged --redact
gitleaks git <checkout> --log-opts='<published-base>..HEAD' --redact
```

Use the suites' documented disposable database safeguards. Do not reuse a pilot,
review or production database for destructive test fixtures. The WP3 command ran
in a writable disposable working directory with reviewed source read-only; no
orchestrator process or Redis worker was started.

## Environment corrections and limitations

The initial Windows-host WP3 collection lacked Redis/fakeredis dependencies; the
existing pinned image supplied them without changing project dependencies. The
first fresh-checkout container run exposed CRLF provenance drift and a read-only
log-directory test setup; LF attributes and a writable disposable test working
directory resolved these issues. The complete suite then passed.

Default Turbopack rejected dependency junctions outside the isolated review root.
Both builds passed with Next's supported webpack mode; no product setting was
changed to conceal this limitation. The initial sandboxed pytest/Node invocations
encountered filesystem/process permissions; authorized filesystem access and Node
in-process test execution resolved them. No failed attempt is counted as a pass.

Gitleaks flagged the known disposable SQLite test-login password as a generic API
key. Only that exact fixture line has an explanatory `gitleaks:allow` annotation;
no test directory or general rule is excluded. The official portable scanner
archive was checked against its release checksum before use. Private reports,
configuration, credentials, raw responses, ledger databases and checkpoints are
not included in review commits.

## Review bases and delivery

The foundation targets the existing published `feature/production-ui-polish-v1`
line. Its authentication, registry and onboarding prerequisites are not assumed to
be identical to current `main`. The AIE-18/composer branch is stacked on that
foundation. WP3's legacy-client fix targets fetched `main`; HTTP instance delivery
is stacked on the separate legacy fix. The existing alternative parameter branch
is preserved and its omitted-field behavior is explained in the legacy PR.

No in-tree push/PR deployment workflow exists in these repositories. GitHub showed
portal deployments labelled Preview, plus a Vercel preview check; WP3 showed only
dynamic dependency/CodeQL analysis and no deployments. No concrete production push
trigger was found, and no deployment protection was disabled. Hidden external
automation cannot be exhaustively attested; inspect checks on the published heads.
CI status is reported separately from the local test results and may be pending.

References: AIE-18; AIE-37 catalogue capability contracts; AIE-39 input configuration.
AIE-18 remains In Review. Production compatibility and independent first-time-user
usability remain unverified. Retained provider/algorithm evidence is historical;
publication and the manual demo create no new execution evidence.
