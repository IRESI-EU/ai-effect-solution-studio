"""Registry-derived context and review for existing logical instances only."""
from copy import deepcopy
from fastapi import HTTPException
from app.models.operation_contract import OperationContract
from app.services.parameter_values import parameter_contract_digest
from app.services.instance_configuration import validate_configuration


def entries(design, db):
    nodes = [n for n in design["nodes"] if n.get("data", {}).get("service")]
    labels = [str(n["data"].get("label") or n["data"]["service"].get("name") or n["id"]) for n in nodes]
    result = []
    for node, label in zip(nodes, labels):
        data, configuration = node["data"], node["data"].get("configuration")
        service = data["service"]
        item = {"node_id": node["id"], "label": label if labels.count(label) == 1 else f"{label} · {node['id']}",
                "operation_name": service["operation_name"], "description": service.get("description", "")}
        try:
            if configuration is None:
                raise HTTPException(409, "This instance has no pinned editable parameter contract")
            effective = validate_configuration(db, service["id"], service["operation_name"], configuration)
            contract = db.get(OperationContract, configuration["contract_id"])
            definition = deepcopy(contract.definition["execution_parameters"])
            item.update(resolution="active", contract_id=contract.id, contract_version=contract.contract_version,
                operation_identity=contract.operation_identity, parameter_contract_sha256=parameter_contract_digest(definition),
                definition=definition, parameters=deepcopy(configuration["parameters"]), effective_parameters=effective["parameters"])
        except HTTPException as exc:
            item.update(resolution="unavailable", limitation=exc.detail)
        result.append(item)
    return result


def settings_context(row, db):
    instances = entries(row.state["design"], db)
    return {"instances": instances, "supported_edits": ["set_node_parameters"] if any(n["resolution"] == "active" for n in instances) else [],
        "parameter_update": "Patch only the requested parameter keys; preserve other settings and the pinned contract",
        "targeting": "Use the logical node_id. Labels identify first/second steps; if the intended instance is ambiguous, ask which label/ID and return no edits.",
        "runtime_checked": False, "execution": "No workflow is submitted by this conversation"}


def parameter_review(before, after, db):
    changed = {n["id"] for n in after["nodes"] if n.get("data", {}).get("configuration") !=
               next((old.get("data", {}).get("configuration") for old in before["nodes"] if old["id"] == n["id"]), None)}
    if not changed:
        return {"changes": [], "unchanged": [], "contract_pins": {}}
    original = {n["node_id"]: n for n in entries(before, db)}
    changes, unchanged, pins = [], [], {}
    for item in entries(after, db):
        if item["node_id"] not in changed:
            if item["resolution"] == "active":
                unchanged.append({"node_id": item["node_id"], "label": item["label"], "parameters": item["effective_parameters"],
                    "titles": {key: spec["title"] for key, spec in item["definition"]["properties"].items()}})
            continue
        if item["resolution"] != "active":
            raise HTTPException(409, "The targeted instance's contract is unavailable; no proposal can be applied")
        old = original[item["node_id"]].get("effective_parameters", {})
        properties = item["definition"]["properties"]
        changes.extend({"node_id": item["node_id"], "label": item["label"], "key": key,
            "title": properties[key]["title"], "description": properties[key]["description"], "before": old.get(key), "after": value}
            for key, value in item["effective_parameters"].items() if old.get(key) != value)
        pins[item["node_id"]] = {key: item[key] for key in ("contract_id", "contract_version", "operation_identity", "parameter_contract_sha256")}
    if not changes:
        raise HTTPException(422, "The proposed settings have the same effective values; nothing changed")
    return {"changes": changes, "unchanged": unchanged, "contract_pins": pins}
