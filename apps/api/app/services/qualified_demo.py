"""One registered Dutch workflow, using existing catalogue/contract authority.

This is recommendation and instantiation, not a new graph synthesizer. Nothing
here invokes a model, starts a workflow, or enables the offline review profile.
"""
from copy import deepcopy
import json
from fastapi import HTTPException
from sqlalchemy.engine import make_url
from app.core.config import settings
from app.models.operation_contract import OperationContract
from app.schemas.design_ai import AssistantTurn
from app.schemas.workflow_submit import WorkflowSubmitRequest
from app.services.instance_configuration import validate_builder_configurations, validate_configuration

SYNTH = "urn:aieffect:nl:configure-and-synthesize:capture"
BENCHMARK = "urn:aieffect:nl:run-benchmark:capture"


def profile_enabled():
    url = make_url(settings.database_url)
    return bool(settings.design_ai_dutch_demo and settings.aie37_qualification
        and url.host in {"postgres", "127.0.0.1"} and url.database == "design_aie37_qualification"
        and settings.orchestrator_base_url == "http://seed-orchestrator:8000")


def inspect(design, db, user):
    from app.services import design_ai, capability_bindings
    validate_builder_configurations(db, design["nodes"], design["edges"], user)
    chain = design_ai.ordered_services(design["nodes"], design["edges"])
    if (design.get("run_input") is not None or len(chain) != 2
        or [node["data"]["service"]["operation_name"] for node in chain] != ["ConfigureAndSynthesize", "RunBenchmark"]):
        raise HTTPException(422, "Only the registered sample-grid generation then benchmark workflow is supported")
    for node, identity in zip(chain, [SYNTH, BENCHMARK]):
        pin = node["data"].get("operation_contract", {})
        contract = db.get(OperationContract, pin.get("contract_id"))
        if not contract or contract.operation_identity != identity or contract.status != "active" or contract.contract_version != pin.get("contract_version"):
            raise HTTPException(409, "A qualified Dutch service or its pinned contract is unavailable")
        service = node["data"]["service"]
        if service.get("status") not in {"approved", "validated"} or service.get("lifecycle_status") == "archived":
            raise HTTPException(409, "A required service is no longer approved and active")
    source = chain[0]["data"]
    configured = validate_configuration(db, source["service"]["id"], source["service"]["operation_name"], source.get("configuration"))
    payload = workflow_payload(design)
    report = capability_bindings.validate(payload, db)
    if not report["bindings"] or len(report["bindings"]) != 1:
        raise HTTPException(409, "The saved generation-to-benchmark connection is unavailable")
    return chain, configured["parameters"]["seed"]


def workflow_payload(design, solution=None):
    services = [node for node in design["nodes"] if node.get("data", {}).get("service")]
    ids = {node["id"] for node in services}
    nodes = []
    for node in services:
        data, service = node["data"], node["data"]["service"]
        value = {"node_id": node["id"], "service_id": service["id"],
            "container_name": service.get("container_name", ""), "operation_name": service["operation_name"],
            "operation_contract": data.get("operation_contract")}
        if "configuration" in data:
            value["configuration"] = data["configuration"]
        nodes.append(value)
    return WorkflowSubmitRequest.model_validate({"name": design["name"], "nodes": nodes,
        "edges": [{"source": edge["source"], "target": edge["target"], "binding": (edge.get("data") or {}).get("binding")}
                  for edge in design["edges"] if edge["source"] in ids and edge["target"] in ids],
        "solution_id": solution.id if solution else None,
        "expected_updated_at": solution.updated_at.isoformat() if solution else None})


def capability(key, value, db, user):
    if not profile_enabled() or key != "dutch":
        raise HTTPException(422, "The qualified Dutch demonstration is not enabled in this profile")
    chain, seed = inspect(value, db, user)
    from app.models.service import Service
    from app.services.catalogue_discovery import eligible, revision as authority_revision
    from app.services.design_ai import policies
    services = [db.query(Service).filter(Service.id == node["data"]["service"]["id"]).populate_existing().one() for node in chain]
    if any(not eligible(service, user) for service in services):
        raise HTTPException(409, "A registered workflow service is no longer approved or accessible")
    # Both legacy and generic Create use the same complete authority fingerprint.
    # Changes to runtime metadata also invalidate a review; no live probe occurs.
    revision = authority_revision(db, user, services, {"source": value["source"], "policy": policies()[key].model_dump()})
    source_contract = db.get(OperationContract, chain[0]["data"]["operation_contract"]["contract_id"])
    seed_spec = (source_contract.definition.get("execution_parameters") or {}).get("properties", {}).get("seed", {})
    declared_default = seed_spec.get("default")
    if type(declared_default) is not int or declared_default not in seed_spec.get("enum", []):
        declared_default = None
    return {"key": key, "label": "Create and benchmark a sample electricity grid", "mechanism": "registered_workflow",
        "scope": "Recommend an existing qualified workflow; arbitrary AI composition is not supported",
        "source_revision": revision, "current_seed": seed, "supported_seeds": [42, 43], "declared_seed_default": declared_default,
        "steps": [{"title": "Create a sample grid", "operation": "ConfigureAndSynthesize"},
                  {"title": "Benchmark the grid produced by the first step", "operation": "RunBenchmark"}],
        "connection": "Benchmark the exact grid produced by the first step",
        "expected_result_view": ["recorded seed", "task states", "grid summary", "recorded benchmark values"],
        "optional_downloads": ["Configuration JSON", "Grid JSON", "Pandapower graph JSON", "Benchmark JSON"],
        "availability": "Results become available only after successful explicit execution and capture",
        "execution_status": "Nothing has been created or executed by this recommendation",
        "limitations": ["Registered workflow recommendation, not arbitrary composition", "Synthetic grid and no-op benchmark agent",
                        "KPI units and scientific validity are not established", "Production compatibility remains unverified"]}


def lock_template(value, db):
    """Hold source/catalogue/contract authority during explicit copy creation."""
    from app.models.solution import Solution
    from app.models.service import Service
    source = db.query(Solution).filter(Solution.id == value['source']['solution_id']).with_for_update().populate_existing().one()
    identifiers = sorted({node['data']['service']['id'] for node in source.nodes if node.get('data', {}).get('service')})
    db.query(Service).filter(Service.id.in_(identifiers)).order_by(Service.id).with_for_update().populate_existing().all()
    db.query(OperationContract).filter(OperationContract.service_id.in_(identifiers)).order_by(OperationContract.id).with_for_update().populate_existing().all()


def seed_turn(row, seed):
    from app.services import design_ai
    if type(seed) is not int or seed not in (42, 43):
        raise HTTPException(422, "Choose a supported integer seed: 42 or 43")
    node = design_ai.ordered_services(row.state["design"]["nodes"], row.state["design"]["edges"])[0]
    configuration = deepcopy(node["data"]["configuration"])
    configuration["parameters"] = {"seed": seed}
    return AssistantTurn(message=f"Review seed {seed} for the sample grid. Benchmark its output; no execution has occurred.",
        template_key="dutch", expected_revision=row.revision, edits=[{"kind": "set_node_parameters", "node_id": node["id"], "value": json.dumps(configuration)}])
