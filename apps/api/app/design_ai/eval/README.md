# Design with AI evaluation set

A fixed benchmark for the model behind **Design with AI**, so any model (OpenAI,
or a small model such as Qwen served on our own GPUs) can be compared on the
same task, with the same prompt, validator and repair loop the portal uses.

| File | What it is |
|---|---|
| `catalogue_snapshot.json` | The 13 connectable catalogue services on staging, frozen on 2026-11-25, plus short aliases (`nl_synth`, `dk_config`, ...). Frozen so scores stay comparable. |
| `cases.jsonl` | 87 test requests with the expected result (one JSON object per line). |
| `scoring.py` | Scoring rules (pure functions, unit-tested in `app/tests/test_design_ai_eval.py`). |
| `run_eval.py` | Runs the cases against a model and writes a JSON + Markdown report. |
| `results/` | Reference runs. `baseline-gpt-4.1-mini-2026-11-25` is the current baseline. |

## Running it

From `apps/api` with the API requirements installed (`pip install -r requirements.txt`),
or inside the API container. No database is needed.

```bash
# OpenAI baseline (key read from an environment variable, never from the command line)
export DESIGN_AI_EVAL_KEY=...            # or: --api-key-env DESIGN_AI_API_KEY inside the API container
python -m app.design_ai.eval.run_eval --model gpt-4.1-mini --price-in 0.37 --price-out 1.47

# A small model on our own GPU, served by vLLM (OpenAI-compatible endpoint, no key)
vllm serve Qwen/Qwen2.5-7B-Instruct --port 8000          # on the GPU machine
python -m app.design_ai.eval.run_eval --base-url http://<gpu-host>:8000/v1 --model Qwen/Qwen2.5-7B-Instruct

# Rule-based offline composer (the floor)
python -m app.design_ai.eval.run_eval --offline
```

Useful options: `--repeat 3` (consistency: run every case three times),
`--only settings,refusal` (categories or case ids), `--workers 4`, `--out <dir>`.

The runner first tries strict JSON-schema output and falls back to JSON mode when
the server refuses it. With vLLM, structured output (guided decoding) makes a
large difference for small models, so keep it enabled.

## What is measured

Each case passes only if all of these hold:

- **Outcome**: a valid workflow when the catalogue covers the request; *no*
  workflow when nothing fits (honest refusal); for partly covered requests, the
  covered part is built (or offered) **and** the reply names the missing capability.
- **Services**: exactly the expected services, no more and no fewer.
- **Settings**: values implied by the request are set correctly (e.g. "heavy load"
  means `loading_level = "H"`, "only the three best" means `how_many = 3`); no
  other values are invented. Setting a value to its declared default is
  counted as *noise*, not an error, because nothing changes at run time.

The report also gives: valid on the first try (before the repair loop), mean
attempts, latency and token use, plus an optional cost estimate.

## Categories

| Category | Cases | Tests |
|---|---|---|
| pipeline | 24 | Plain-language requests for each node's pipeline, no node names |
| settings | 19 | Turning words into setting values |
| limits | 3 | Values beyond the allowed range (must clamp or leave unset) |
| multi | 5 | Several goals, all covered, from different nodes |
| partial | 6 | Some goals not covered; must say which |
| refusal | 12 | Nothing fits; must not build a workflow |
| followup | 8 | Changing a workflow already on the canvas |
| robustness | 10 | Typos, German/Dutch/Portuguese/Danish, instructions hidden in the request, vague requests |

## Baseline (gpt-4.1-mini, 3 runs per case)

98% pass rate, 100% right outcome, 90% valid on first try, 2.9 s mean latency,
about €0.35 for 261 requests. Its one consistent failure is `multi-04`
(German time series together with Portuguese synthetic data). Full report:
`results/baseline-gpt-4.1-mini-2026-11-25.md`.

## Adding cases

Add one JSON line to `cases.jsonl`:

```json
{"id": "settings-nl-07", "category": "settings", "prompt": "Benchmark controllers on a grid with seed 5",
 "expect": {"outcome": "workflow", "services": ["nl_synth", "nl_bench"], "settings": {"nl_synth": {"seed": 5}}}}
```

Optional fields: `settings_optional` (values allowed but not required),
`missing_keywords` (for `partial`), `history` and `current` (for follow-ups:
`{"services": [...], "settings": {...}}` becomes a chain on the canvas), `note`.
`outcome` is one of `workflow`, `partial`, `refusal`, `clarify_or_workflow`.
Run `pytest app/tests/test_design_ai_eval.py`: it checks every case refers to
real services and valid setting values.

When the catalogue changes, export a new snapshot under a new name rather than
editing this one, so earlier results stay comparable.

## Keep the evaluation cases out of training data

If the cases are used to train a model, its score here no longer means
anything. Generate training data from *other* prompts and keep `cases.jsonl` as
held-out test data only.
