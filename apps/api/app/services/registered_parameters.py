"""Bounded registered design configuration using the canonical Builder validators.

Only the retained experimental Portuguese chain is supported. This supplies no
runtime authority and does not change the native-only catalogue pair composer.
"""
from copy import deepcopy
import json
from uuid import uuid4

from fastapi import HTTPException

from app.models.operation_contract import OperationContract
from app.schemas.design_ai import AssistantTurn
from app.schemas.workflow_submit import WorkflowSubmitRequest
from app.services import capability_bindings
from app.services.instance_configuration import validate_configuration

SERVICES = ["pt-experimental-chain-TrainModel", "pt-experimental-chain-GenerateData"]
PINS = ["pt-chain-train-v2", "pt-chain-generate-v2"]


def input_choice(registration, user_id):
    deployment = registration.deployment_design_input
    if deployment is None:
        return capability_bindings.sandbox_training_input(user_id)
    from app.core.config import settings
    from app.services.shared_allowance import database_scope
    try:
        matches = (not capability_bindings.sandbox_profile_enabled()
            and settings.design_ai_registration_environment == deployment.environment
            and database_scope(settings.database_url) == deployment.database_scope
            and user_id == registration.reviewer_id)
    except ValueError:
        matches = False
    return {"label": deployment.label, "dataset_ref": deployment.dataset_ref} if matches else None


def training_input(user_id, db):
    """Reuse registry authority; expose only the current actor's label/reference."""
    sandbox = capability_bindings.sandbox_training_input(user_id)
    if sandbox is not None:
        return sandbox
    from app.services import design_ai
    try:
        policy = design_ai.policies().get("portugal")
        if not policy or not policy.registered_parameters or not policy.registered_parameters.deployment_design_input:
            return None
        from app.models.user import User
        current = db.get(User, user_id)
        if current is None or input_choice(policy.registered_parameters, user_id) is None:
            return None
        source = design_ai.source_solution("portugal", db)
        authority("portugal", policy, source, db, current)
        return input_choice(policy.registered_parameters, user_id)
    except HTTPException:
        return None


def validate_target_input(workflow, db, user):
    from app.core.config import settings
    if (not settings.design_ai_registration_environment or capability_bindings.sandbox_profile_enabled()
        or not any(n.service_id in SERVICES for n in workflow.nodes)):
        return
    from app.services import design_ai
    design_ai.template("portugal", db, user)
    policy = design_ai.policies()["portugal"].registered_parameters
    if not policy or not policy.deployment_design_input:
        raise HTTPException(403, "This environment has no approved experimental design registration")
    choice = input_choice(policy, user.id)
    if choice is None or workflow.run_input != {"dataset_ref": choice["dataset_ref"]}:
        raise HTTPException(422, "Select the authorized training CSV before validating.")


def authority(key, policy, source, db, user):
    from app.services import design_ai
    from app.services.catalogue_discovery import actor, eligible
    from app.models.service import Service
    registration = policy.registered_parameters
    current = actor(db,user)
    if (key != "portugal"
        or current.id != registration.reviewer_id or source.created_by_user_id != current.id
        or input_choice(registration, current.id) is None):
        raise HTTPException(403,"This experimental workflow is registered only for its configured environment and reviewer")
    if design_ai.digest(design_ai.content(source)) != registration.source_revision:
        raise HTTPException(409,"The registered source changed; operator review is required")
    nodes = design_ai.ordered_services(source.nodes,source.edges,instance_settings_only=True)
    if [n["data"]["service"]["id"] for n in nodes] != SERVICES:
        raise HTTPException(409,"Only the registered experimental TrainModel → GenerateData chain is supported")
    if set(registration.contract_definitions) != set(PINS):
        raise HTTPException(409,"The registration must pin both reviewed contract definitions")
    for node,identity in zip(nodes,PINS):
        service=db.query(Service).filter(Service.id==node["data"]["service"]["id"]).populate_existing().first()
        pin=db.query(OperationContract).filter(OperationContract.id==identity).populate_existing().first()
        if (not service or not eligible(service,current) or not pin or pin.status!="active"
            or pin.service_id!=service.id or pin.contract_version!="0.2.0"
            or capability_bindings.digest(pin.definition)!=registration.contract_definitions[identity]
            or node["data"].get("operation_contract")!={"contract_id":identity,"contract_version":"0.2.0"}):
            raise HTTPException(409,"The registered operation, approval or contract pin changed")
    from app.services.instance_configuration import validate_builder_configurations
    validate_builder_configurations(db,source.nodes,source.edges,current)


def initial_design(value,db):
    nodes=deepcopy(value["nodes"]);edges=deepcopy(value["edges"])
    identities={node["id"]:str(uuid4()) for node in nodes}
    for node in nodes:
        node["id"]=identities[node["id"]]
        data=node["data"]
        # Copy design fields only, never source execution/capture metadata.
        node["data"]={k:deepcopy(data[k]) for k in ("node_kind","service","label","operation_contract") if k in data}
        if data.get("service"):
            service=data["service"];pin=data["operation_contract"]
            config={**pin,"parameters":{}}
            defaults=validate_configuration(db,service["id"],service["operation_name"],config)
            node["data"]["configuration"]={**pin,"parameters":defaults["parameters"]}
    edges=[{"id":str(uuid4()),"source":identities[e["source"]],"target":identities[e["target"]],
            **({"data":{"binding":deepcopy(e["data"]["binding"])}} if e.get("data",{}).get("binding") else {})} for e in edges]
    return {"name":"Portuguese registered workflow — AI design","description":"Experimental sandbox design; no execution has occurred.",
        "nodes":nodes,"edges":edges,"run_input":None,"input_policy":None,"editing_scope":"instance_settings",
        "registered_workflow":value["source"]["registration_id"],
        **({"execution_policy":value["source"]["execution_policy"]} if value["source"].get("execution_policy") else {})}


def validate_input(value,user,db=None):
    if value is None or value=={}:return None
    choice=training_input(user.id,db)
    if not choice or value!={"dataset_ref":choice["dataset_ref"]}:
        raise HTTPException(422,"Select the authorized sandbox training CSV; other data references are unsupported")
    return deepcopy(value)


def workflow(design):
    nodes=[n for n in design["nodes"] if n.get("data",{}).get("service")];ids={n["id"] for n in nodes}
    return WorkflowSubmitRequest(name=design["name"],run_input=design.get("run_input"),
        nodes=[{"node_id":n["id"],"service_id":n["data"]["service"]["id"],"container_name":"registry","operation_name":"registry",
            "configuration":n["data"]["configuration"],"operation_contract":n["data"]["operation_contract"]} for n in nodes],
        edges=[{"source":e["source"],"target":e["target"],"binding":e.get("data",{}).get("binding")} for e in design["edges"] if e["source"] in ids and e["target"] in ids])


def validation(design,db,user):
    from app.services.solution_design import hydrate_solution_service_references
    from app.services.workflow_compiler import compile_to_wp3_payload
    try:
        validate_input(design.get("run_input"),user,db)
        hydrate_solution_service_references(db,design["nodes"],user)
        capability_bindings.validate_builder(design["nodes"],design["edges"],db)
        if design.get("run_input") is None:
            raise HTTPException(422,"Select a training CSV before validating.")
        compile_to_wp3_payload(workflow(design),db)
        return {"valid":True,"errors":[],"unknown":["Design compatibility only. INSPECTION ONLY: no runtime readiness, execution or scientific-quality claim."],"required_inputs":[]}
    except HTTPException as exc:
        return {"valid":False,"errors":[exc.detail],"unknown":[],"required_inputs":[{"operation":"TrainModel","name":"dataset_ref","resolution":"selection_required"}]}


def capability(value,db,user):
    from app.services.instance_proposals import entries
    from app.services.catalogue_discovery import text
    design=initial_design(value,db)
    # Public, bounded registry metadata only; no endpoints, paths, data or tokens.
    return {"key":value["key"],"label":"Experimental Portuguese training and generation", "mechanism":"registered_workflow",
        "configuration_kind":"registered_parameters","registration_id":value["source"]["registration_id"],
        "steps":[{"title":"Train a model","operation":"TrainModel"},{"title":"Generate sequences from that model","operation":"GenerateData"}],
        "connection":"Published model_ref → model_ref whole-output-v1 binding; generation uses the model from this design's training step.",
        "required_inputs":[{"name":"dataset_ref","required":True,"source":"visible_selection","label":"Training CSV",
            "choices":[training_input(user.id,db)]}],
        "registered_operations":[{"step":index, "operation":item["operation_name"],"parameters":{
            **item["definition"],"properties":{name:{**spec,"title":text(spec["title"],120),"description":text(spec["description"],240)}
                for name,spec in item["definition"]["properties"].items()}}}
            for index,item in enumerate(entries(design,db))],
        "expected_result_view":[],"optional_downloads":[],"runtime_checked":False,"execution_supported":False,
        "availability":"INSPECTION ONLY. New executions require a separate bounded supervised authorization.",
        "limitations":["Platform-controlled experimental sidecar, not Portuguese-owner approval or hosted qualification.",
            "CSV and conservative bounds are sandbox choices. New designs inherit no execution results or authority."]}


def configuration_turn(row,settings,run_input,db,user):
    from app.services import design_ai
    if not row.state["design"].get("registered_workflow"):
        raise HTTPException(422,"This design has no registered configuration controls")
    values=validate_input(run_input,user,db)
    nodes=design_ai.service_nodes(row.state["design"]["nodes"])
    if set(settings)-{n["id"] for n in nodes}:
        raise HTTPException(422,"Choose a current registered operation instance")
    edits=[]
    if values!=row.state["design"].get("run_input"):
        edits.append({"kind":"set_run_input","node_id":None,"value":json.dumps(values)})
    for node in nodes:
        if node["id"] in settings:
            config={**node["data"]["configuration"],"parameters":settings[node["id"]]}
            if config!=node["data"]["configuration"]:
                edits.append({"kind":"set_node_parameters","node_id":node["id"],"value":json.dumps(config)})
    if not edits:raise HTTPException(422,"Choose a different supported setting or training input before review")
    return AssistantTurn(message="Review these explicit configuration changes. No AI request or workflow execution occurred.",
        template_key=None,expected_revision=row.revision,edits=edits)


def recommendation(item,choice):
    from app.schemas.design_ai import CompositionSettings
    from app.services.parameter_values import effective_parameters
    choice=choice or CompositionSettings();values={}
    for step,spec in zip(("first","second"),item["registered_operations"]):
        assignments=getattr(choice,step)
        if len({v.name for v in assignments})!=len(assignments):raise HTTPException(422,"Duplicate registered setting")
        try:params=effective_parameters(spec["parameters"],{v.name:v.value for v in assignments})
        except ValueError as exc:raise HTTPException(422,str(exc)) from None
        values[step]=[{"name":k,"value":v} for k,v in params.items()]
    return {**{k:v for k,v in item.items() if not k.startswith('_')},"registered_settings":values,"recommendation_revision":item["revision"]}


def propose_recommendation(result,values,db,user):
    from app.services import design_ai
    row=design_ai.load_draft(result["id"],db,user)
    nodes=design_ai.ordered_services(row.state["design"]["nodes"],row.state["design"]["edges"],instance_settings_only=True)
    settings={node["id"]:{v["name"]:v["value"] for v in values[step]} for step,node in zip(("first","second"),nodes)}
    if all(settings[n["id"]]==n["data"]["configuration"]["parameters"] for n in nodes):return result
    return design_ai.propose(row.id,configuration_turn(row,settings,None,db,user),db,user)
