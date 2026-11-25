"""Load evaluation cases and score one Design with AI answer against them.

Pure functions only (no network, no database) so the scoring rules can be
unit-tested and reused by the runner and by training-data filters.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from app.design_ai.catalogue import ServiceCard

HERE = Path(__file__).parent
DEFAULT_SNAPSHOT = HERE / "catalogue_snapshot.json"
DEFAULT_CASES = HERE / "cases.jsonl"
OUTCOMES = ("workflow", "partial", "refusal", "clarify_or_workflow")


@dataclass
class Snapshot:
    name: str
    aliases: dict[str, str]
    cards: list[ServiceCard]

    def resolve(self, alias_or_id: str) -> str:
        return self.aliases.get(alias_or_id, alias_or_id)


def load_snapshot(path: Path = DEFAULT_SNAPSHOT) -> Snapshot:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    cards = [ServiceCard(**card) for card in data["cards"]]
    return Snapshot(data.get("snapshot", Path(path).stem), data.get("aliases", {}), cards)


def load_cases(path: Path = DEFAULT_CASES) -> list[dict[str, Any]]:
    cases = []
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if line.strip() and not line.lstrip().startswith("//"):
            try:
                cases.append(json.loads(line))
            except ValueError as exc:
                raise ValueError(f"{path}:{number}: {exc}") from exc
    return cases


def _resolve_settings(raw: dict | None, snap: Snapshot) -> dict[str, dict[str, Any]]:
    return {snap.resolve(k): dict(v) for k, v in (raw or {}).items()}


def case_history(case: dict) -> list[dict[str, str]]:
    return [*case.get("history", []), {"role": "user", "content": case["prompt"]}]


def case_current(case: dict, snap: Snapshot) -> dict | None:
    """Turn ``{"services": [...], "settings": {...}}`` into a linear canvas workflow."""
    current = case.get("current")
    if not current:
        return None
    settings = _resolve_settings(current.get("settings"), snap)
    ids = [snap.resolve(s) for s in current["services"]]
    steps = [{"ref": f"s{i + 1}", "service_id": sid, "why": "", "settings": settings.get(sid, {})} for i, sid in enumerate(ids)]
    connections = [{"from_ref": f"s{i + 1}", "to_ref": f"s{i + 2}"} for i in range(len(ids) - 1)]
    return {"steps": steps, "connections": connections}


def validate_case(case: dict, snap: Snapshot) -> list[str]:
    """Problems with the case itself (unknown services, settings outside the schema)."""
    from app.services.service_settings import resolve_values

    problems: list[str] = []
    by_id = {c.id: c for c in snap.cards}
    expect = case.get("expect") or {}
    if expect.get("outcome") not in OUTCOMES:
        problems.append(f"unknown outcome {expect.get('outcome')!r}")
    if expect.get("outcome") in ("workflow", "partial") and not expect.get("services"):
        problems.append("workflow cases need expected services")
    if expect.get("outcome") == "partial" and not expect.get("missing_keywords"):
        problems.append("partial cases need missing_keywords")
    used = list(expect.get("services") or []) + list((case.get("current") or {}).get("services", []))
    for alias in used:
        if snap.resolve(alias) not in by_id:
            problems.append(f"unknown service {alias!r}")
    for key in ("settings", "settings_optional"):
        for sid, values in _resolve_settings(expect.get(key), snap).items():
            card = by_id.get(sid)
            if card is None or not card.settings:
                problems.append(f"{key}: {sid} has no declared settings")
                continue
            _, errors = resolve_values(card.settings, values)
            problems.extend(f"{key}: {sid}: {e}" for e in errors)
    return problems


@dataclass
class CaseScore:
    case_id: str
    category: str
    passed: bool
    outcome_ok: bool
    services_ok: bool | None = None
    settings_ok: bool | None = None
    valid: bool = False
    first_try_valid: bool = False
    attempts: int = 0
    chosen_services: list[str] = field(default_factory=list)
    chosen_settings: dict[str, dict[str, Any]] = field(default_factory=dict)
    explicit_defaults: int = 0
    problems: list[str] = field(default_factory=list)
    reply: str = ""
    clarifying_question: str | None = None
    latency_s: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _check_settings(expected: dict, optional: dict, chosen: dict, names: dict[str, str], defaults: dict) -> tuple[list[str], int]:
    """Return (problems, number of settings explicitly set to their default).

    Setting a value to its declared default changes nothing at run time, so it
    is counted as noise rather than an error.
    """
    problems, explicit_defaults = [], 0
    for sid in set(expected) | set(chosen):
        want, got, may = expected.get(sid, {}), chosen.get(sid, {}), optional.get(sid, {})
        label = names.get(sid, sid)
        for name, value in want.items():
            if name not in got:
                problems.append(f"{label}: setting {name} missing (expected {value!r})")
            elif got[name] != value or type(got[name]) is not type(value):
                problems.append(f"{label}: setting {name} = {got[name]!r}, expected {value!r}")
        for name, value in got.items():
            if name in want:
                continue
            if name in may and may[name] == value:
                continue
            if name in defaults.get(sid, {}) and defaults[sid][name] == value:
                explicit_defaults += 1
                continue
            problems.append(f"{label}: unexpected setting {name} = {value!r}")
    return problems, explicit_defaults


def score_case(case: dict, snap: Snapshot, result: Any, latency_s: float = 0.0) -> CaseScore:
    """Score a CompositionResult-like object (reply, clarifying_question, workflow, errors, attempts)."""
    expect = case["expect"]
    outcome = expect["outcome"]
    workflow = result.workflow
    valid = workflow is not None and not result.errors
    score = CaseScore(
        case_id=case["id"], category=case.get("category", ""), passed=False, outcome_ok=False,
        valid=valid, first_try_valid=valid and result.attempts == 1, attempts=result.attempts,
        reply=result.reply, clarifying_question=result.clarifying_question, latency_s=round(latency_s, 2),
        prompt_tokens=getattr(result, "prompt_tokens", 0), completion_tokens=getattr(result, "completion_tokens", 0),
    )
    names = {c.id: c.name for c in snap.cards}
    if workflow:
        score.chosen_services = [s["service_id"] for s in workflow["steps"]]
        score.chosen_settings = {s["service_id"]: s["settings"] for s in workflow["steps"] if s["settings"]}
    if result.errors:
        score.problems.extend(f"invalid after {result.attempts} attempts: {e}" for e in result.errors)

    text = f"{result.reply} {result.clarifying_question or ''}".lower()
    has_question = bool((result.clarifying_question or "").strip())

    if outcome == "refusal":
        score.outcome_ok = workflow is None and not result.errors
        if workflow is not None:
            score.problems.append("built a workflow although nothing in the catalogue fits")
        score.passed = score.outcome_ok
        return score

    if outcome == "clarify_or_workflow" and workflow is None and has_question and not result.errors:
        score.outcome_ok = score.passed = True
        return score

    if outcome == "partial" and workflow is None and has_question and not result.errors:
        # Asking "shall I build the part that is covered?" is acceptable, if it names the gap.
        keywords = [k.lower() for k in expect.get("missing_keywords", [])]
        score.outcome_ok = score.passed = any(k in text for k in keywords)
        if not score.passed:
            score.problems.append(f"reply does not say which goal is not covered (looked for: {', '.join(keywords)})")
        return score

    if not valid:
        score.problems.append("no valid workflow")
        return score
    score.outcome_ok = True
    if outcome == "partial":
        keywords = [k.lower() for k in expect.get("missing_keywords", [])]
        if not any(k in text for k in keywords):
            score.outcome_ok = False
            score.problems.append(f"reply does not say which goal is not covered (looked for: {', '.join(keywords)})")

    if expect.get("services"):
        want = {snap.resolve(s) for s in expect["services"]}
        got = set(score.chosen_services)
        score.services_ok = want == got
        for sid in sorted(want - got):
            score.problems.append(f"missing service {names.get(sid, sid)}")
        for sid in sorted(got - want):
            score.problems.append(f"unexpected service {names.get(sid, sid)}")

    defaults = {
        c.id: {n: p["default"] for n, p in c.settings["schema"]["properties"].items() if "default" in p}
        for c in snap.cards if c.settings
    }
    setting_problems, score.explicit_defaults = _check_settings(
        _resolve_settings(expect.get("settings"), snap), _resolve_settings(expect.get("settings_optional"), snap),
        score.chosen_settings, names, defaults,
    )
    score.settings_ok = not setting_problems
    score.problems.extend(setting_problems)
    score.passed = score.outcome_ok and score.services_ok is not False and score.settings_ok
    return score


def summarise(scores: list[CaseScore]) -> dict[str, Any]:
    def rate(items: list[CaseScore], attr: str) -> float | None:
        values = [getattr(s, attr) for s in items if getattr(s, attr) is not None]
        return round(sum(bool(v) for v in values) / len(values), 3) if values else None

    categories = sorted({s.category for s in scores})
    answered = [s for s in scores if s.error is None]
    return {
        "cases": len(scores),
        "errors": len(scores) - len(answered),
        "pass_rate": rate(scores, "passed"),
        "outcome_rate": rate(scores, "outcome_ok"),
        "services_rate": rate(scores, "services_ok"),
        "settings_rate": rate(scores, "settings_ok"),
        "first_try_valid_rate": rate([s for s in scores if s.category != "refusal"], "first_try_valid"),
        "explicit_defaults": sum(s.explicit_defaults for s in scores),
        "mean_attempts": round(sum(s.attempts for s in answered) / len(answered), 2) if answered else None,
        "mean_latency_s": round(sum(s.latency_s for s in answered) / len(answered), 2) if answered else None,
        "prompt_tokens": sum(s.prompt_tokens for s in scores),
        "completion_tokens": sum(s.completion_tokens for s in scores),
        "by_category": {
            c: {"cases": len(items), "pass_rate": rate(items, "passed")}
            for c in categories
            for items in [[s for s in scores if s.category == c]]
        },
    }
