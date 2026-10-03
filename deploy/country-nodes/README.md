# Country-node production overlays

These overlays remove public host-port bindings and give services unambiguous
names on the shared `ai-effect-services` network. Always pass the country
repository's Compose file first so that relative build paths still resolve from
the country source tree.

Pinned source revisions for the first release candidate:

- German, Portuguese, Danish: `AI-EFFECT/ai-effect-wp3` at
  `e8914565e966a2d78879c314f980574769d31b87`
- Dutch: `paulban/ai-effect-wp3` at
  `ba598b2459f9986dac4e37dcc5d7d3298f25dc3a`

The Portuguese stack also requires `data/real_data.csv` and a server-only
`PORTUGAL_CLICKHOUSE_PASSWORD` value. Never commit either a production password
or restricted input data to this repository.

The Dutch workflow consists of two independently composed services. Start both
the synthesizer and benchmark stacks with their matching overlays. Their
production Docker aliases are `grid_synth_service` and `benchmark-runner`; the
aliases replace the Windows-only `host.docker.internal` addresses in the sample
metadata.
