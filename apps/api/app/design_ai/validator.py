"""Check a proposed workflow with the same rules the Builder applies.

A proposal is ``{"steps": [{"ref", "service_id", "why", "settings"}],
"connections": [{"from_ref", "to_ref"}]}``. ``settings`` may be a dict or the
model's list form ``[{"name", "value_json"}]``.
"""

from __future__ import annotations

import json
from typing import Any

from app.design_ai.catalogue import ServiceCard
from app.services.service_settings import resolve_values


def _settings_dict(raw: Any, errors: list[str], label: str) -> dict[str, Any]:
    if raw in (None, [], {}):
        return {}
    if isinstance(raw, dict):
        return raw
    values: dict[str, Any] = {}
    for item in raw if isinstance(raw, list) else []:
        name = (item or {}).get("name")
        try:
            values[name] = json.loads(item.get("value_json", "null"))
        except (TypeError, ValueError):
            errors.append(f"{label}: the value for setting '{name}' is not valid JSON.")
    return values


def validate_proposal(proposal: dict | None, cards: list[ServiceCard]) -> tuple[dict | None, list[str]]:
    """Return (normalised workflow, errors). Errors are written for the model and the user."""
    if not proposal:
        return None, []
    by_id = {card.id: card for card in cards}
    errors: list[str] = []
    steps_out: list[dict[str, Any]] = []
    refs: dict[str, ServiceCard] = {}
    runtime_keys: dict[str, str] = {}

    steps = proposal.get("steps") or []
    if not steps:
        return None, ["The workflow has no steps."]

    for index, step in enumerate(steps):
        ref = str(step.get("ref") or f"s{index + 1}")
        card = by_id.get(step.get("service_id"))
        if card is None:
            errors.append(f"Step {ref}: service_id '{step.get('service_id')}' is not an approved catalogue service.")
            continue
        if ref in refs:
            errors.append(f"Step reference '{ref}' is used twice.")
            continue
        key = f"{card.container_name}:{card.operation}"
        if key in runtime_keys:
            errors.append(f"{card.name} is used twice; one service cannot appear twice in a workflow.")
            continue
        runtime_keys[key] = ref
        refs[ref] = card
        values = _settings_dict(step.get("settings"), errors, card.name)
        if values and not card.settings:
            errors.append(f"{card.name} has fixed settings; remove the settings for this step.")
            values = {}
        elif values:
            _, setting_errors = resolve_values(card.settings, values)
            errors.extend(f"{card.name}: {e}" for e in setting_errors)
        steps_out.append({
            "ref": ref,
            "service_id": card.id,
            "service_name": card.name,
            "provider": card.provider,
            "why": str(step.get("why") or "").strip(),
            "settings": values,
        })

    connections_out: list[dict[str, str]] = []
    incoming: dict[str, int] = {ref: 0 for ref in refs}
    adjacency: dict[str, list[str]] = {ref: [] for ref in refs}
    for conn in proposal.get("connections") or []:
        source, target = conn.get("from_ref"), conn.get("to_ref")
        if source not in refs or target not in refs:
            errors.append(f"Connection {source} -> {target} refers to an unknown step.")
            continue
        if source == target:
            errors.append(f"Step {source} cannot connect to itself.")
            continue
        a, b = refs[source], refs[target]
        if a.output_type != b.input_type:
            errors.append(
                f"{a.name} cannot feed {b.name}: it produces '{a.output_type}' but {b.name} needs '{b.input_type}'."
            )
            continue
        if {"from_ref": source, "to_ref": target} in connections_out:
            continue
        connections_out.append({"from_ref": source, "to_ref": target})
        incoming[target] += 1
        adjacency[source].append(target)

    # No loops (orchestrator workflows are acyclic).
    visiting, done = set(), set()

    def has_cycle(node: str) -> bool:
        visiting.add(node)
        for nxt in adjacency[node]:
            if nxt in visiting or (nxt not in done and has_cycle(nxt)):
                return True
        visiting.discard(node)
        done.add(node)
        return False

    if any(has_cycle(r) for r in refs if r not in done):
        errors.append("The connections form a loop; workflows must flow in one direction.")

    for step in steps_out:
        card = refs[step["ref"]]
        if incoming[step["ref"]] == 0 and not card.is_start and len(refs) > 1:
            errors.append(f"{card.name} needs input '{card.input_type}' but nothing is connected to it.")
        if card.settings and card.settings["channel"] == "run_input" and incoming[step["ref"]] > 0 and step["settings"]:
            errors.append(f"{card.name} reads its settings from the workflow input, so it must be a first step.")

    return {"steps": steps_out, "connections": connections_out}, errors
