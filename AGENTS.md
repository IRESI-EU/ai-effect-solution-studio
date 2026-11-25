# Working on this repository

- `main` must match what is deployed on https://platform.ai-effect.eu/ (plus reviewed, not-yet-deployed PRs). Never deploy a commit that is not on `main`.
- Work in small, reviewable pull requests. The repository owner (GitHub `adarshsunil`) approves every merge.
- Each PR states: what changed, how to try it (click-by-click), and what was tested. No separate evidence or checkpoint documents.
- Keep product code generic: no service-, node- or demo-specific branches in core code. Node-specific setup belongs in configuration or seed data.
- Back up the production database before every deployment.

Current plan and dates: [docs/ROADMAP.md](docs/ROADMAP.md).
