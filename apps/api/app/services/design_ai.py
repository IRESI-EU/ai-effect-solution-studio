"""Bounded design operations shared by HTTP and the private MCP server.

No runtime probes, artifact fetches, deployments or repository onboarding here.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException
from jsonschema import Draft202012Validator
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.design_ai import DesignDraft
from app.models.operation_contract import OperationContract
from app.models.solution import Solution
from app.models.user import User
from app.schemas.design_ai import AssistantTurn
from app.services.audit import record_audit_event
from app.services.solution_design import hydrate_solution_service_references, service_id_from_builder_node
from app.services.instance_configuration import validate_builder_configurations, validate_configuration


PILOTS = {
    "denmark": ("Danish SysLAB", ["BuildRunConfig", "GenerateTopology", "RenderTopologies"]),
    "dutch": ("Dutch Node", ["ConfigureAndSynthesize", "RunBenchmark"]),
    "portugal": ("Portugal", None),
    "germany": ("Germany", ["ProvideData", "GenerateChronics", "FormatOutput"]),
}


class InputPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    service_id: str
    operation_name: str
    evidence_reference: str = Field(min_length=1)
    json_schema: dict


class TemplatePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    solution_id: str | None = None
    solution_name: str | None = None
    run_input: InputPolicy | None = None
    instance_settings_only: bool = False
    structural_append_only: bool = False

    @model_validator(mode="after")
    def selector(self):
        if bool(self.solution_id) == bool(self.solution_name):
            raise ValueError("Provide exactly one template selector")
        if self.instance_settings_only and self.structural_append_only:
            raise ValueError("Select exactly one editing scope")
        if self.run_input:
            schema = self.run_input.json_schema
            Draft202012Validator.check_schema(schema)
            if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
                raise ValueError("Run input needs a closed object schema")
            if "$ref" in json.dumps(schema):
                raise ValueError("References are not supported in pilot input schemas")
        return self


def enabled() -> None:
    if not settings.design_ai_enabled:
        raise HTTPException(404, "Design with AI is disabled")


def policies() -> dict[str, TemplatePolicy]:
    enabled()
    try:
        raw = json.loads(settings.design_ai_templates or "{}")
        if not isinstance(raw, dict) or set(raw) - set(PILOTS):
            raise ValueError("Unknown pilot key")
        return {key: TemplatePolicy.model_validate(value) for key, value in raw.items()}
    except Exception as exc:
        raise HTTPException(503, "Pilot template configuration is invalid. Contact the operator.") from exc


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, allow_nan=False).encode()).hexdigest()


def content(solution: Solution) -> dict:
    return {"name": solution.name, "description": solution.description or "", "nodes": solution.nodes,
            "edges": solution.edges, "design_metadata": solution.design_metadata}


def source_solution(key: str, db: Session) -> Solution:
    policy = policies().get(key)
    if not policy:
        raise HTTPException(404, "This pilot template has not been configured")
    query = db.query(Solution).filter(Solution.status != "archived")
    query = query.filter(Solution.id == policy.solution_id) if policy.solution_id else query.filter(Solution.name == policy.solution_name)
    matches = query.limit(2).all()
    if not matches:
        raise HTTPException(409, "The configured template is missing or archived")
    if len(matches) != 1:
        raise HTTPException(409, "The configured template name is ambiguous. Ask the operator to select one ID.")
    return matches[0]


def service_nodes(nodes: list[dict]) -> list[dict]:
    return [node for node in nodes if service_id_from_builder_node(node)]


def ordered_services(nodes: list[dict], edges: list[dict], *, instance_settings_only: bool = False) -> list[dict]:
    """Accept only a single connected chain, with optional Builder boundaries."""
    if not isinstance(nodes, list) or not isinstance(edges, list) or not nodes or len(nodes) > 30 or len(edges) > 40 or any(not isinstance(node, dict) for node in nodes):
        raise HTTPException(422, "This pilot supports small linear saved workflows")
    ids = [node.get("id") for node in nodes]
    if any(not isinstance(item, str) or not item for item in ids) or len(set(ids)) != len(ids):
        raise HTTPException(422, "Workflow node IDs are missing or duplicated")
    incoming = {item: [] for item in ids}
    outgoing = {item: [] for item in ids}
    edge_ids, pairs = set(), set()
    for edge in edges:
        if not isinstance(edge, dict):
            raise HTTPException(422, "A saved workflow connection is malformed")
        start, end = edge.get("source"), edge.get("target")
        if not isinstance(start, str) or not isinstance(end, str) or start not in outgoing or end not in incoming or start == end:
            raise HTTPException(422, "Workflow connection does not resolve to distinct nodes")
        if (start, end) in pairs or not isinstance(edge.get("id"), str) or not edge["id"] or edge["id"] in edge_ids:
            raise HTTPException(422, "Workflow connections are duplicated or have missing IDs")
        if edge.get("sourceHandle") or edge.get("targetHandle"):
            raise HTTPException(422, "Named port bindings are not preserved by the current compiler")
        edge_ids.add(edge["id"])
        pairs.add((start, end))
        outgoing[start].append(end)
        incoming[end].append(start)
    roots = [key for key in ids if not incoming[key]]
    if len(roots) != 1 or any(len(incoming[key]) > 1 or len(outgoing[key]) > 1 for key in ids):
        raise HTTPException(422, "Branching, merging or disconnected workflows are outside this pilot")
    ordered, cursor = [], roots[0]
    by_id = {node["id"]: node for node in nodes}
    while cursor not in ordered:
        ordered.append(cursor)
        if not outgoing[cursor]:
            break
        cursor = outgoing[cursor][0]
    if len(ordered) != len(ids):
        raise HTTPException(422, "The workflow is disconnected or cyclic")
    result = [by_id[key] for key in ordered if service_id_from_builder_node(by_id[key])]
    boundaries = [by_id[key] for key in ordered if not service_id_from_builder_node(by_id[key])]
    if any(node.get("type") not in {"input", "output"} for node in boundaries):
        raise HTTPException(422, "An unrecognized workflow node cannot be copied into this pilot")
    if any((node.get("type") == "input" and node["id"] != ordered[0]) or
           (node.get("type") == "output" and node["id"] != ordered[-1]) for node in boundaries):
        raise HTTPException(422, "Workflow boundaries must be at the beginning and end of the service chain")
    if not result:
        raise HTTPException(422, "The workflow has no services")
    if not instance_settings_only and len({service_id_from_builder_node(node) for node in result}) != len(result):
        raise HTTPException(422, "Repeated instances of one wrapper are not supported by this pilot")
    return result


def template(key: str, db: Session, user: User) -> dict:
    source = source_solution(key, db)
    policy = policies()[key]
    raw = deepcopy(source.nodes)
    ordered_services(raw, source.edges, instance_settings_only=policy.instance_settings_only)
    nodes = hydrate_solution_service_references(db, raw, user)
    chain = ordered_services(nodes, source.edges, instance_settings_only=policy.instance_settings_only)
    if policy.instance_settings_only:
        validate_builder_configurations(db, nodes, source.edges, user)
        for node in chain:
            data = node["data"]
            if "configuration" not in data:
                raise HTTPException(409, "Settings-only copies require a pinned parameter contract on every service instance")
            validate_configuration(db, data["service"]["id"], data["service"]["operation_name"], data["configuration"])
    # A saved operation must still refer to the current wrapper, not silently change on hydration.
    old_services = {n["id"]: n.get("data", {}).get("service", {}) for n in service_nodes(raw)}
    for node in chain:
        service = node["data"]["service"]
        if not service.get("operation_name"):
            raise HTTPException(409, "A template service has no declared runtime operation")
        if service.get("status") not in {"approved", "validated"} or service.get("lifecycle_status") == "archived":
            raise HTTPException(409, "This template contains a service that is not approved and active")
        old_op = old_services.get(node["id"], {}).get("operation_name")
        if old_op and old_op != service["operation_name"]:
            raise HTTPException(409, "A template operation differs from the current catalogue. Operator review is required.")
    actual = [n["data"]["service"]["operation_name"] for n in chain]
    expected = PILOTS[key][1]
    if not policy.instance_settings_only and not policy.structural_append_only and ((expected and actual != expected) or (key == "portugal" and len(chain) != 4)):
        raise HTTPException(409, "The saved operations or connections do not match this pilot candidate")
    if policy.structural_append_only:
        validate_builder_configurations(db, nodes, source.edges, user)
        if (source.design_metadata or {}).get("run_input") is not None or policy.run_input is not None:
            raise HTTPException(422, "Structural whole-output copies do not support workflow-input routing")
        if any(not n["data"].get("operation_contract") for n in chain):
            raise HTTPException(409, "Structural copies require verified pinned operation contracts")
    if policy.run_input:
        first = chain[0]["data"]["service"]
        if (policy.run_input.service_id, policy.run_input.operation_name) != (first["id"], first["operation_name"]):
            raise HTTPException(409, "The configured run input does not target this workflow's first operation")
    return {"key": key, "label": PILOTS[key][0], "source": {"solution_id": source.id,
            "revision": digest(content(source)), "updated_at": source.updated_at.isoformat() if source.updated_at else None,
            "reference_kind": "mutable_saved_design", "execution_snapshot": None},
            "name": source.name, "description": source.description or "", "nodes": nodes,
            "edges": deepcopy(source.edges), "input_policy": policy.run_input.model_dump() if policy.run_input else None,
            "editing_scope": "instance_settings" if policy.instance_settings_only else "append_bound_operation" if policy.structural_append_only else None,
            "run_input": deepcopy((source.design_metadata or {}).get("run_input")),
            "reference_note": ("Separate settings copy of the selected saved design. Historical execution snapshots remain separate; no experiment has run."
                if policy.instance_settings_only else "Separate composition copy; historical execution snapshots remain separate. No workflow has run for this copy."
                if policy.structural_append_only else "Copied saved design. No immutable deployment snapshot is stored by this platform; previous execution equivalence is unverified.")}


def list_templates(db: Session, user: User) -> list[dict]:
    configured = policies()
    result = []
    for key, (label, _) in PILOTS.items():
        item = {"key": key, "label": label, "available": False}
        if key in configured and configured[key].instance_settings_only:
            item["editing_scope"] = "instance_settings"
        if key in configured and configured[key].structural_append_only:
            item["editing_scope"] = "append_bound_operation"
        if key not in configured:
            item["reason"] = "Not configured by the operator"
        else:
            try:
                value = template(key, db, user)
                item.update(available=True, description=value["description"], operations=[n["data"]["service"]["operation_name"] for n in ordered_services(value["nodes"], value["edges"], instance_settings_only=policy_scope(value))])
                item["guided_available"] = guided_policy(key, value["input_policy"])
            except HTTPException as exc:
                item["reason"] = exc.detail if isinstance(exc.detail, str) else "Referenced services are missing or inaccessible"
        result.append(item)
    return result


def contracts(nodes: list[dict], db: Session) -> list[dict]:
    result = []
    for node in service_nodes(nodes):
        service = node["data"]["service"]
        matches = db.query(OperationContract).filter(OperationContract.service_id == service["id"], OperationContract.status == "active",
                    OperationContract.runtime_operation_name == service["operation_name"]).all()
        contract = matches[0] if len(matches) == 1 else None
        result.append({"node_id": node["id"], "service_id": service["id"], "operation_name": service["operation_name"],
            "resolution": "active" if contract else "unknown", "contract_id": contract.id if contract else None,
            "version": contract.contract_version if contract else None, "definition": contract.definition if contract else None})
    return result


def validate(design: dict, db: Session, user: User) -> dict:
    errors, unknown, required = [], [], []
    try:
        validate_builder_configurations(db, design["nodes"], design["edges"], user)
        nodes = hydrate_solution_service_references(db, design["nodes"], user)
        chain = ordered_services(nodes, design["edges"], instance_settings_only=policy_scope(design))
        for node in chain:
            saved = next(n for n in design["nodes"] if n["id"] == node["id"])["data"]["service"]
            current = node["data"]["service"]
            if saved["operation_name"] != current["operation_name"] or current["status"] not in {"approved", "validated"} or current["lifecycle_status"] == "archived":
                errors.append("A service operation or approval changed. Start from a reviewed template.")
    except HTTPException as exc:
        return {"valid": False, "errors": [exc.detail if isinstance(exc.detail, str) else "A catalogue service is missing or inaccessible"], "unknown": [], "required_inputs": []}
    resolved = contracts(nodes, db)
    by_node = {item["node_id"]: item for item in resolved}
    first_node_id = chain[0]["id"]
    for upstream, downstream in zip(chain, chain[1:]):
        left, right = by_node[upstream["id"]], by_node[downstream["id"]]
        if left["definition"] and right["definition"]:
            outputs = left["definition"].get("outputs", [])
            inputs = [slot for slot in right["definition"].get("inputs", [])
                      if slot.get("source_requirement") in {"upstream_operation", "upstream_or_workflow_input"}]
            if len(outputs) == len(inputs) == 1:
                output, input_slot = outputs[0], inputs[0]
                if any(output.get(field) != input_slot.get(field) for field in ("semantic_concept", "value_representation")):
                    errors.append(f"Declared contract mismatch between {left['operation_name']} and {right['operation_name']}")
                if output.get("value_representation") == "data_reference":
                    for field in ("data_reference_protocols", "content_types"):
                        a, b = set(output.get(field, [])), set(input_slot.get(field, []))
                        if a and b and not a.intersection(b):
                            errors.append(f"Declared {field} do not overlap between connected operations")
                if output.get("schema_ref") and input_slot.get("schema_ref") and output["schema_ref"] != input_slot["schema_ref"]:
                    unknown.append("Connected operations declare different schemas; conversion is not verified.")
    for item in resolved:
        if item["resolution"] == "unknown":
            unknown.append(f"{item['operation_name']}: no unique active operation contract")
        else:
            for slot in item["definition"].get("inputs", []):
                if slot.get("required"):
                    required.append({"operation": item["operation_name"], "name": slot["name"], "source_requirement": slot["source_requirement"], "resolution": "unknown"})
                    requirement = slot["source_requirement"]
                    if requirement == "workflow_input" and item["node_id"] != first_node_id:
                        errors.append(f"{item['operation_name']} requires direct workflow input that the current compiler cannot route to a downstream operation")
                    elif item["node_id"] == first_node_id:
                        if requirement == "upstream_operation":
                            errors.append(f"{item['operation_name']} requires an upstream operation but is first in this chain")
                        elif requirement in {"workflow_input", "upstream_or_workflow_input"} and design.get("run_input") is None:
                            errors.append(f"{item['operation_name']} requires workflow input; supply verified supported input before saving")
    from app.services.capability_bindings import validate_builder
    binding_report = validate_builder(nodes, design["edges"], db)
    if binding_report["status"] == "verified":
        for item in required:
            item["resolution"] = "verified"
        unknown.append("Design binding compatibility verified; live runtime availability and production compatibility remain unchecked.")
    else:
        unknown.append("Legacy connections: semantic compatibility and required-slot delivery remain unverified.")
    policy = design.get("input_policy")
    run_input = design.get("run_input")
    if policy_scope(design):
        pass  # Existing workflow input is copied unchanged; this scope cannot edit it.
    elif run_input is not None:
        if not policy:
            errors.append("This template has no verified editable run input")
        else:
            for error in Draft202012Validator(policy["json_schema"]).iter_errors(run_input):
                errors.append(f"Run input at {'.'.join(map(str, error.path)) or 'root'}: {error.message}")
    elif policy and policy["json_schema"].get("required"):
        errors.append("Provide the required run input fields: " + ", ".join(policy["json_schema"]["required"]))
    return {"valid": not errors, "errors": errors, "unknown": unknown, "required_inputs": required,
            "contracts": [{"node_id": item["node_id"], "resolution": item["resolution"], "version": item["version"]} for item in resolved]}


def load_draft(draft_id: str, db: Session, user: User, lock: bool = False) -> DesignDraft:
    enabled()
    query = db.query(DesignDraft).filter(DesignDraft.id == draft_id, DesignDraft.owner_id == user.id)
    # A Session may already hold this row from validation before taking the
    # lock. Refresh the identity map after acquiring it, including after a wait
    # for another writer, so revision checks cannot use stale cached content.
    row = (query.populate_existing().with_for_update() if lock else query).first()
    if not row:
        raise HTTPException(404, "Draft not found")
    # Revocation of operator sharing takes effect for existing sessions too.
    if row.state["template_key"] not in policies():
        raise HTTPException(409, "This pilot template is no longer enabled")
    if source_solution(row.state["template_key"], db).id != row.state["source"]["solution_id"]:
        raise HTTPException(409, "The operator selected a different source. Start a new copy.")
    if policies()[row.state["template_key"]].instance_settings_only != policy_scope(row.state["design"]):
        raise HTTPException(409, "The supported editing scope changed. Start a new copy.")
    if policies()[row.state["template_key"]].structural_append_only != (row.state["design"].get("editing_scope") == "append_bound_operation"):
        raise HTTPException(409, "The structural editing scope changed. Start a new copy.")
    current_policy = policies()[row.state["template_key"]].run_input
    if digest(current_policy.model_dump() if current_policy else None) != digest(row.state["design"].get("input_policy")):
        raise HTTPException(409, "Supported input configuration changed. Start a new copy.")
    return row


def list_drafts(db: Session, user: User) -> list[dict]:
    """Read-only, owner-scoped resume choices; opening still uses load_draft guards."""
    enabled()
    rows = db.query(DesignDraft).filter(DesignDraft.owner_id == user.id).order_by(DesignDraft.updated_at.desc(), DesignDraft.id).all()
    return [{"id": row.id, "name": row.state["design"]["name"], "revision": row.revision,
             "updated_at": row.updated_at, "dirty": row.state["dirty"],
             "saved_solution_id": row.state.get("saved_solution_id"),
             "pending_changes": bool(row.state.get("pending")),
             "seed": (row.state["design"].get("run_input") or {}).get("seed")}
            for row in rows]


def view(row: DesignDraft, db: Session | None = None) -> dict:
    state = deepcopy(row.state)
    state.pop("history", None)
    state.pop("saved_fingerprint", None)
    result = {"id": row.id, "revision": row.revision, "can_undo": bool(row.state.get("history")), **state}
    if db is not None and policy_scope(state["design"]):
        from app.services.instance_proposals import settings_context
        result["instance_settings"] = settings_context(row, db)["instances"]
    return result


def policy_scope(design: dict) -> bool:
    return design.get("editing_scope") == "instance_settings"


def guided_policy(key: str, policy: dict | None) -> bool:
    schema = (policy or {}).get("json_schema", {})
    return key == "dutch" and set(schema.get("properties", {})) == {"seed"} and not list(Draft202012Validator(schema).iter_errors({"seed": 42}))


def guided_context(row: DesignDraft) -> dict | None:
    facts = guided_capabilities(row.state["template_key"], row.state["design"],
                                guided=row.state.get("guided_experiment") == "dutch_sample_grid")
    if facts is not None:
        facts["execution_status"] = "Not inspected for this draft; this conversation does not execute a workflow"
    return facts


def guided_capabilities(key: str, design: dict, *, guided: bool) -> dict | None:
    """Same verified scope for a recommendation or draft; never creates a draft."""
    from app.services import local_dutch_capture as capture
    from app.services.dutch_capture_contract import NODE_KEYS
    if (not guided or not capture.enabled()
            or not guided_policy(key, design.get("input_policy"))):
        return None
    chain = ordered_services(design["nodes"], design["edges"])
    keys = [node["data"]["service"].get("container_name", "") + ":" + node["data"]["service"]["operation_name"] for node in chain]
    if keys != [NODE_KEYS["synth"], NODE_KEYS["benchmark"]]:
        return None
    return {"scope": "Verified local Dutch guided interface and automatic capture; not a resolved operation contract",
            "steps": [{"title": "Generate sample grid", "operation": "ConfigureAndSynthesize"},
                      {"title": "Benchmark grid", "operation": "RunBenchmark"}],
            "connection": "The generated sample electricity grid is passed to the benchmark",
            "expected_result_view": ["recorded seed settings", "task progress", "grid summary", "recorded benchmark values"],
            "optional_downloads": list(capture.LABELS.values()),
            "availability": "Results and downloads depend on explicit confirmed execution and successful capture; outputs may be unavailable",
            "execution_status": "No execution evidence supplied; this conversation does not create or execute a workflow",
            "limitations": ["No grid counts predicted before execution", "No supplied KPI units or physical safety/optimality evidence",
                            "Missing operation contracts remain unresolved", "Production compatibility remains unverified"]}



def discovery_capability(key: str, db: Session, user: User) -> dict:
    value = template(key, db, user)  # Re-check source sharing, approval and governance.
    facts = guided_capabilities(key, value, guided=key == "dutch")
    if facts is None:
        raise HTTPException(422, "This request is outside the supported local sample-grid experiment. No experiment was created.")
    return {"key": key, "label": "Generate and benchmark a sample electricity grid.", **facts}


def start(key: str, db: Session, user: User, *, guided: bool = False) -> dict:
    value = template(key, db, user)
    design = {"name": value["name"] + " — AI draft", "description": value["description"],
              "nodes": value["nodes"], "edges": value["edges"], "run_input": None, "input_policy": value["input_policy"]}
    if policy_scope(value):
        design.update(editing_scope="instance_settings", run_input=value["run_input"])
    if value.get("editing_scope") == "append_bound_operation":
        design.update(editing_scope="append_bound_operation", run_input=value["run_input"])
    if guided:
        if not guided_policy(key, value["input_policy"]):
            raise HTTPException(422, "The guided Dutch experiment needs an approved seed input policy")
        design.update(name="Sample electricity grid experiment", run_input={"seed": 42})
        for node in service_nodes(design["nodes"]):
            operation = node["data"]["service"]["operation_name"]
            node["data"]["label"] = {"ConfigureAndSynthesize": "Generate sample grid.", "RunBenchmark": "Benchmark grid."}[operation]
        validation = validate(design, db, user)
        if not validation["valid"]:
            raise HTTPException(422, "The guided experiment is unavailable: " + "; ".join(validation["errors"]))
    row = DesignDraft(id=str(uuid4()), owner_id=user.id, revision=0, state={"template_key": key, "source": value["source"],
          "reference_note": value["reference_note"], "design": design, "validation": validate(design, db, user),
          "history": [], "edit_history": [], "pending": None, "saved_solution_id": None, "guided_experiment": "dutch_sample_grid" if guided else None,
          "reserved_solution_id": str(uuid4()), "saved_revision": None, "dirty": True})
    db.add(row)
    db.commit()
    return view(row, db)


def guided_settings(draft_id: str, revision: int, seed: int, db: Session, user: User) -> dict:
    row = load_draft(draft_id, db, user)
    if not guided_policy(row.state["template_key"], row.state["design"].get("input_policy")):
        raise HTTPException(422, "Guided settings are unavailable for this template")
    turn = AssistantTurn(message="Review the seed change, then Apply changes.", template_key="dutch", expected_revision=revision,
        edits=[{"kind": "set_run_input", "value": json.dumps({"seed": seed}), "node_id": None}])
    # Reuses the locked revision check, schema validation and explicit Apply/Undo path.
    return propose(draft_id, turn, db, user)


def check_revision(row: DesignDraft, revision: int) -> None:
    if row.revision != revision:
        raise HTTPException(409, "The draft changed. Refresh it before trying again.")


def candidate(row: DesignDraft, turn: AssistantTurn, db: Session, user: User, *, allocation: str | None = None) -> tuple[dict, dict]:
    check_revision(row, turn.expected_revision)
    if turn.template_key is not None and turn.template_key != row.state["template_key"]:
        raise HTTPException(422, "Start a new copy to change templates")
    design = deepcopy(row.state["design"])
    structural = design.get("editing_scope") == "append_bound_operation"
    if structural and (len(turn.edits) != 1 or turn.edits[0].kind != "append_bound_operation"):
        raise HTTPException(422, "This structural scope supports one bound append only; existing settings stay unchanged")
    for edit in turn.edits:
        if edit.kind == "append_bound_operation":
            if not structural:
                raise HTTPException(422, "Select a structural composition copy before adding an operation")
            from app.services.structural_proposals import append
            design = append(design, edit, allocation or str(uuid4()), db, user)
        elif policy_scope(design) and edit.kind != "set_node_parameters":
            raise HTTPException(422, "This copy supports instance-setting changes only; its structure, labels and workflow input stay fixed")
        if edit.kind == "rename":
            if not edit.value.strip() or len(edit.value) > 160:
                raise HTTPException(422, "Use a draft name between 1 and 160 characters")
            design["name"] = edit.value.strip()
        elif edit.kind == "describe":
            if len(edit.value) > 4000:
                raise HTTPException(422, "The description is too long")
            design["description"] = edit.value
        elif edit.kind == "set_node_label":
            matches = [n for n in service_nodes(design["nodes"]) if n["id"] == edit.node_id]
            if len(matches) != 1 or not edit.value.strip() or len(edit.value) > 100:
                raise HTTPException(422, "Choose a current service node and a short display label")
            matches[0]["data"]["label"] = edit.value.strip()
        elif edit.kind == "set_run_input":
            if not design.get("input_policy"):
                raise HTTPException(422, "No verified wrapper input is configured for this template")
            try:
                design["run_input"] = json.loads(edit.value, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
            except ValueError as exc:
                raise HTTPException(422, "The proposed run input is not valid JSON") from exc
        elif edit.kind == "set_node_parameters":
            matches = [n for n in service_nodes(design["nodes"]) if n["id"] == edit.node_id]
            if len(matches) != 1:
                raise HTTPException(422, "Choose a current node instance")
            try:
                configuration = json.loads(edit.value)
            except ValueError as exc:
                raise HTTPException(422, "Instance configuration must be valid JSON") from exc
            service = matches[0]["data"]["service"]
            if policy_scope(design):
                original = matches[0]["data"]["configuration"]
                if not isinstance(configuration, dict) or set(configuration) != {"contract_id", "contract_version", "parameters"}:
                    raise HTTPException(422, "Use the pinned contract and a parameter object")
                if any(configuration[key] != original[key] for key in ("contract_id", "contract_version")):
                    raise HTTPException(409, "The proposal must keep this instance's pinned contract identity and version")
                if not isinstance(configuration["parameters"], dict):
                    raise HTTPException(422, "Parameters must be an object")
                configuration = {**configuration, "parameters": {**original["parameters"], **configuration["parameters"]}}
            validate_configuration(db, service["id"], service["operation_name"], configuration)
            matches[0]["data"]["configuration"] = configuration
    result = validate(design, db, user)
    return design, result


def propose(draft_id: str, turn: AssistantTurn, db: Session, user: User) -> dict:
    row = load_draft(draft_id, db, user, lock=True)
    allocation = str(uuid4())
    design, validation = candidate(row, turn, db, user, allocation=allocation)
    from app.services.instance_proposals import parameter_review
    review = parameter_review(row.state["design"], design, db)
    state = deepcopy(row.state)
    state["pending"] = {"id": str(uuid4()), "base_revision": row.revision, "turn": turn.model_dump(), "design": design, "validation": validation,
                        "parameter_review": review}
    if row.state["design"].get("editing_scope") == "append_bound_operation":
        from app.services.structural_proposals import review as structural_review
        state["pending"].update(allocation=allocation, structural_review=structural_review(row.state["design"], design, db, user))
    row.state = state
    db.commit()
    return view(row, db)


def apply(draft_id: str, revision: int, proposal_id: str, db: Session, user: User) -> dict:
    row = load_draft(draft_id, db, user, lock=True)
    check_revision(row, revision)
    pending = row.state.get("pending")
    if not pending or pending["id"] != proposal_id:
        raise HTTPException(409, "This proposal is no longer current")
    design, validation = candidate(row, AssistantTurn.model_validate(pending["turn"]), db, user, allocation=pending.get("allocation"))
    from app.services.instance_proposals import parameter_review
    if parameter_review(row.state["design"], design, db) != pending.get("parameter_review", {"changes": [], "unchanged": [], "contract_pins": {}}):
        raise HTTPException(409, "The parameter contract or review changed. Request a new proposal before Apply.")
    if row.state["design"].get("editing_scope") == "append_bound_operation":
        from app.services.structural_proposals import review as structural_review
        if design != pending["design"] or structural_review(row.state["design"], design, db, user) != pending.get("structural_review"):
            raise HTTPException(409, "The catalogue, contract or structural review changed. Request a new proposal.")
    if not validation["valid"]:
        raise HTTPException(422, "The proposed change cannot be applied: " + "; ".join(validation["errors"]))
    state = deepcopy(row.state)
    state["history"] = (state["history"] + [{"design": state["design"], "validation": state["validation"]}])[-30:]
    state.update(design=design, validation=validation, pending=None, dirty=True)
    state["edit_history"] = (state["edit_history"] + [{"revision": revision + 1, "edits": [e["kind"] for e in pending["turn"]["edits"]]}])[-100:]
    row.state, row.revision, row.updated_at = state, revision + 1, datetime.utcnow()
    db.commit()
    return view(row, db)


def undo(draft_id: str, revision: int, db: Session, user: User) -> dict:
    row = load_draft(draft_id, db, user, lock=True)
    check_revision(row, revision)
    state = deepcopy(row.state)
    if not state["history"]:
        raise HTTPException(409, "There is no applied change to undo")
    previous = state["history"].pop()
    state.update(previous)
    state.update(pending=None, dirty=True)
    state["edit_history"] = (state["edit_history"] + [{"revision": revision + 1, "edits": ["undo"]}])[-100:]
    row.state, row.revision = state, revision + 1
    db.commit()
    return view(row, db)


def save(draft_id: str, revision: int, db: Session, user: User, *, explicit_save: bool = False) -> dict:
    if not explicit_save:
        raise HTTPException(403, "Saving requires the explicit Save draft action")
    row = load_draft(draft_id, db, user, lock=True)
    check_revision(row, revision)
    state = deepcopy(row.state)
    current_validation = validate(state["design"], db, user)
    if not current_validation["valid"]:
        raise HTTPException(422, "Resolve the draft input or catalogue errors before saving")
    solution_id = state["reserved_solution_id"]
    if solution_id == state["source"]["solution_id"]:
        raise HTTPException(409, "The source template cannot be overwritten")
    solution = db.query(Solution).filter(Solution.id == solution_id).with_for_update().first()
    if solution:
        if solution.created_by_user_id != user.id or digest(content(solution)) != state.get("saved_fingerprint") or solution.status != "draft":
            raise HTTPException(409, "The saved solution was changed in Builder. Start a new AI copy to avoid overwriting it.")
        if not state["dirty"]:
            return view(row, db)
    else:
        solution = Solution(id=solution_id, created_by_user_id=user.id, status="draft")
        db.add(solution)
    design = state["design"]
    validate_builder_configurations(db, design["nodes"], design["edges"], user)
    solution.name, solution.description = design["name"], design["description"]
    solution.nodes, solution.edges = deepcopy(design["nodes"]), deepcopy(design["edges"])
    solution.design_metadata = {"origin": "design_ai", "source": state["source"], "draft_id": row.id,
        "guided_experiment": state.get("guided_experiment"),
        "draft_revision": row.revision, "run_input": design["run_input"], "validation": current_validation,
        "edit_history": state["edit_history"]}
    solution.updated_at = datetime.utcnow()
    state.update(saved_solution_id=solution.id, saved_revision=row.revision, dirty=False,
                 saved_fingerprint=digest(content(solution)), validation=current_validation)
    row.state = state
    record_audit_event(db, user, "solution.ai_draft_saved", "solution", solution.id, {"draft_revision": revision})
    db.commit()
    return view(row, db)
