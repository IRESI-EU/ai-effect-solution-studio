# Design with AI evaluation: gpt-4.1-mini

- Endpoint: https://api.openai.com/v1  
- Catalogue snapshot: staging-2026-11-25, cases: 261, run: 2026-11-25T13:17:21Z

| Metric | Value |
|---|---|
| **Pass rate** | **98%** |
| Right outcome (workflow / honest refusal) | 100% |
| Right services | 99% |
| Right settings | 100% |
| Valid on first try | 90% |
| Settings set to their default (noise, not an error) | 24 |
| Mean attempts | 1.08 |
| Mean latency | 2.92 s |
| Tokens (prompt / completion) | 692,094 / 65,187 |
| Model errors | 0 |
| Estimated cost | €0.352 |

| Category | Cases | Pass rate |
|---|---|---|
| followup | 24 | 100% |
| limits | 9 | 100% |
| multi | 15 | 80% |
| partial | 18 | 100% |
| pipeline | 72 | 99% |
| refusal | 36 | 100% |
| robustness | 30 | 100% |
| settings | 57 | 98% |

## Failed cases

- **pipeline-de-02**: no valid workflow
- **settings-dk-06**: config_assistant1 / BuildRunConfig: setting how_many missing (expected 1)
- **multi-04**: missing service data_provider1 / ProvideData; missing service output_formatter1 / FormatOutput; missing service villas_chronics1 / GenerateChronics
- **multi-04**: missing service data_provider1 / ProvideData; missing service output_formatter1 / FormatOutput; missing service villas_chronics1 / GenerateChronics
- **multi-04**: missing service data_provider1 / ProvideData; missing service output_formatter1 / FormatOutput; missing service villas_chronics1 / GenerateChronics
