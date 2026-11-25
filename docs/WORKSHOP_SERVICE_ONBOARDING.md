# Workshop: onboard one service from each node

This exercise demonstrates the difference between registering service metadata
and operating a production container. It uses workshop-labelled copies of four
real AI-EFFECT services. The approved production services already exist, so the
copies must remain `pending_review` and should be archived after the workshop.

## Prepared examples

| Node | Workshop service | Operation | Why it is a useful example |
|---|---|---|---|
| Germany | German Data Provider | `ProvideData` | Shows a workflow entry service that publishes input data for chronic generation. |
| Portugal | Portuguese Data Loader | `ExecuteQuery` | Shows a data-source operation at the start of the integrated synthetic-data pipeline. |
| Denmark | Danish Configuration Assistant | `BuildRunConfig` | Shows prompt/configuration normalization before topology generation. |
| Dutch | Dutch Grid Synthesizer | `ConfigureAndSynthesize` | Shows grid-data synthesis feeding the benchmarking service. |

The German, Portuguese and Danish examples are derived from commit
`e8914565e966a2d78879c314f980574769d31b87` of
`AI-EFFECT/ai-effect-wp3`. The Dutch example is derived from commit
`ba598b2459f9986dac4e37dcc5d7d3298f25dc3a` of
`paulban/ai-effect-wp3`.

## Live demonstration

1. Sign in as a Platform Administrator or Node Manager and open **Publish service**.
2. Under **Workshop examples**, select one country. The portal switches to
   pasted-manifest mode, loads the manifest and records the pinned source revision.
3. Select **Preview pasted manifest**.
4. Explain the validation result, service identity, Docker runtime, operation,
   DataReference input/output types and Control Interface metadata.
5. In **Runtime evidence**, explain that registration does not deploy a container.
   Leave evidence unchecked unless it has actually been verified for that runtime.
6. For a read-only demonstration, stop after preview. For a full governance
   demonstration, accept the registration boundary and submit the request.
7. Open **Admin Governance** and show the pending record. Do not approve the
   workshop copy because the real service is already approved and active.
8. Archive the workshop record after the demonstration.

## Recommended workshop narrative

Use Germany to demonstrate the complete registration form. Use the country
buttons for Portugal, Denmark and the Dutch node to show that the same contract
applies across different node implementations. Then open **Catalogue** and
**Build solution** to show the already-approved production services. This keeps
the distinction clear:

- **Publish service** registers and governs metadata.
- The IT or node operator builds/starts the Docker runtime and verifies health.
- **Admin Governance** approves the service only after that evidence is checked.
- **Build solution** composes approved, running services into workflows.

## Safety rules

- Never mark an evidence checkbox merely for the demonstration.
- Never approve a `[Workshop]` service.
- Do not expose secrets in a manifest or screenshot.
- Prefer immutable commit SHAs and image digests for real onboarding.
- Archive workshop records after the session so they cannot be confused with
  production catalogue entries.
