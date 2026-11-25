"""Run the Design with AI evaluation set against any OpenAI-compatible model.

Uses the real composer (same prompt, validator and repair loop as the portal)
with the frozen catalogue snapshot, so no database is needed.

Examples (from apps/api):

    # OpenAI
    DESIGN_AI_EVAL_KEY=sk-... python -m app.design_ai.eval.run_eval --model gpt-4.1-mini

    # Small model served locally by vLLM or Ollama (no key needed)
    python -m app.design_ai.eval.run_eval --base-url http://gpu-box:8000/v1 --model Qwen/Qwen2.5-7B-Instruct

    # Rule-based offline composer, as a floor
    python -m app.design_ai.eval.run_eval --offline
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from app.design_ai.composer import compose
from app.design_ai.eval.scoring import (
    DEFAULT_CASES, DEFAULT_SNAPSHOT, CaseScore, case_current, case_history, load_cases, load_snapshot,
    score_case, summarise, validate_case,
)
from app.design_ai.providers import ModelError, OfflineModel, OpenAICompatibleModel


def run_case(model, snap, case) -> CaseScore:
    started = time.perf_counter()
    try:
        result = compose(model, snap.cards, case_history(case), case_current(case, snap))
    except ModelError as exc:
        return CaseScore(case_id=case["id"], category=case.get("category", ""), passed=False, outcome_ok=False,
                         error=str(exc), latency_s=round(time.perf_counter() - started, 2))
    return score_case(case, snap, result, time.perf_counter() - started)


def markdown_report(meta: dict, summary: dict, scores: list[CaseScore]) -> str:
    pct = lambda v: "-" if v is None else f"{v * 100:.0f}%"  # noqa: E731
    lines = [
        f"# Design with AI evaluation: {meta['model']}",
        "",
        f"- Endpoint: {meta['base_url']}  ",
        f"- Catalogue snapshot: {meta['snapshot']}, cases: {summary['cases']}, run: {meta['started_at']}",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| **Pass rate** | **{pct(summary['pass_rate'])}** |",
        f"| Right outcome (workflow / honest refusal) | {pct(summary['outcome_rate'])} |",
        f"| Right services | {pct(summary['services_rate'])} |",
        f"| Right settings | {pct(summary['settings_rate'])} |",
        f"| Valid on first try | {pct(summary['first_try_valid_rate'])} |",
        f"| Settings set to their default (noise, not an error) | {summary['explicit_defaults']} |",
        f"| Mean attempts | {summary['mean_attempts']} |",
        f"| Mean latency | {summary['mean_latency_s']} s |",
        f"| Tokens (prompt / completion) | {summary['prompt_tokens']:,} / {summary['completion_tokens']:,} |",
        f"| Model errors | {summary['errors']} |",
    ]
    if meta.get("cost_eur") is not None:
        lines.append(f"| Estimated cost | €{meta['cost_eur']:.3f} |")
    lines += ["", "| Category | Cases | Pass rate |", "|---|---|---|"]
    lines += [f"| {c} | {v['cases']} | {pct(v['pass_rate'])} |" for c, v in summary["by_category"].items()]
    failed = [s for s in scores if not s.passed]
    if failed:
        lines += ["", "## Failed cases", ""]
        for s in failed:
            reason = s.error or "; ".join(s.problems) or "wrong outcome"
            lines.append(f"- **{s.case_id}**: {reason}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default="https://api.openai.com/v1")
    parser.add_argument("--model", default="gpt-4.1-mini")
    parser.add_argument("--api-key-env", default="DESIGN_AI_EVAL_KEY", help="environment variable holding the API key (empty for local servers)")
    parser.add_argument("--offline", action="store_true", help="use the rule-based offline composer")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--only", help="comma-separated case ids or categories to run")
    parser.add_argument("--repeat", type=int, default=1, help="run every case N times (to measure consistency)")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--price-in", type=float, help="EUR per million prompt tokens, for a cost estimate")
    parser.add_argument("--price-out", type=float, help="EUR per million completion tokens")
    parser.add_argument("--out", type=Path, default=Path("design-ai-eval-results"))
    args = parser.parse_args(argv)

    snap = load_snapshot(args.snapshot)
    cases = load_cases(args.cases)
    problems = {c["id"]: p for c in cases if (p := validate_case(c, snap))}
    if problems:
        for cid, p in problems.items():
            print(f"case {cid}: {'; '.join(p)}", file=sys.stderr)
        return 2
    if args.only:
        wanted = {w.strip() for w in args.only.split(",")}
        cases = [c for c in cases if c["id"] in wanted or c.get("category") in wanted]

    if args.offline:
        model = OfflineModel()
        base_url = "offline"
    else:
        model = OpenAICompatibleModel(args.base_url, os.environ.get(args.api_key_env, ""), args.model, args.timeout)
        base_url = args.base_url
    started_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    jobs = [c for c in cases for _ in range(args.repeat)]
    print(f"Running {len(jobs)} cases against {model.model} ({base_url}) ...", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        scores = list(pool.map(lambda c: run_case(model, snap, c), jobs))

    summary = summarise(scores)
    meta = {"model": model.model, "base_url": base_url, "snapshot": snap.name, "started_at": started_at, "repeat": args.repeat}
    if args.price_in is not None and args.price_out is not None:
        meta["cost_eur"] = summary["prompt_tokens"] / 1e6 * args.price_in + summary["completion_tokens"] / 1e6 * args.price_out

    args.out.mkdir(parents=True, exist_ok=True)
    stem = f"{started_at.replace(':', '')}_{model.model.replace('/', '_')}"
    (args.out / f"{stem}.json").write_text(
        json.dumps({"meta": meta, "summary": summary, "cases": [s.to_dict() for s in scores]}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    report = markdown_report(meta, summary, scores)
    (args.out / f"{stem}.md").write_text(report, encoding="utf-8")
    print(report)
    print(f"Results written to {args.out / stem}.json / .md", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
