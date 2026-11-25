# Roadmap: service settings and Design with AI

Updated 23 November 2026.

| Target | Outcome |
| --- | --- |
| 24 Nov | `main` reconciled with production; inventory of which catalogue services accept settings |
| 27 Nov | Same workflow run twice with different settings (local) |
| 2 Dec | Browser journey: publisher declares settings → designer sets values → Run → results |
| 4 Dec | Service settings on staging |
| 11 Dec | Design with AI on staging: prompt → runnable workflow on the canvas |
| 18 Dec | Production rollout |

## Principles

- **Service settings** expose values a service already reads at run time (the `parameters` field of `/control/execute`) or at start-up (environment variables). Services with values fixed in their code are shown as "fixed settings"; no node has to change its service.
- **Design with AI** uses a pluggable model provider over a catalogue description (operations, input/output types, settings). A validator checks every connection and setting, so smaller models can be swapped in later.

The earlier Codex delivery plan is kept for reference in [docs/archive](docs/archive/CODEX_PRODUCTION_DELIVERY_PLAN_2026-11-22.md).
