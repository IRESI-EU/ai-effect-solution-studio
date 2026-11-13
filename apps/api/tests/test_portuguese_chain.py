"""OFFLINE Portal route/contract tests; no provider, algorithm or live worker."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from app.db import SessionLocal
from app.models.operation_contract import OperationContract
from app.models.service import Service
from app.schemas.operation_contract import OperationContractWrite

CONTRACTS=json.loads((Path(__file__).resolve().parents[3]/"deploy/portuguese_sandbox/chain_contracts.json").read_text())


@pytest.fixture
def chained(environment):
    with SessionLocal() as db:
        for c in CONTRACTS:
            value=OperationContractWrite.model_validate({k:v for k,v in c.items() if k not in {"id","service_id"}})
            db.add(Service(id=c["service_id"],name=value.runtime_operation_name,provider="Platform experimental",
                category="experimental-portuguese",description="Offline contract fixture",status="approved",lifecycle_status="active",
                input_type="reference",output_type="reference",operation_name=value.runtime_operation_name,
                container_name="pt-chain-"+value.runtime_operation_name,internal_host="adapter",internal_port="8080",
                image="sha256:experimental",interface_type="control",orchestration_mode="sidecar",adapter_type="platform-experimental",
                contract_uri=value.operation_identity))
            db.flush();values=value.model_dump();values["definition"]=value.definition.model_dump(mode="json",exclude_none=True)
            db.add(OperationContract(id=c["id"],service_id=c["service_id"],status="active",**values))
        db.commit()
    nodes=[]
    for method in ("TrainModel","GenerateData"):
        c=next(c for c in CONTRACTS if c["runtime_operation_name"]==method)
        nodes.append({"id":"train" if method=="TrainModel" else "generate","position":{"x":100,"y":100},
            "data":{"node_kind":"service","service":{"id":c["service_id"]},
                "operation_contract":{"contract_id":c["id"],"contract_version":"0.2.0"},
                "configuration":{"contract_id":c["id"],"contract_version":"0.2.0","parameters":
                    {"epochs":2,"batch_size":4} if method=="TrainModel" else {"number_of_examples":10}}}})
    payload={"name":"Chained experimental fixture","nodes":nodes,"edges":[{"id":"handoff","source":"train","target":"generate",
        "data":{"binding":{"source_slot":"model_ref","target_slot":"model_ref"}}}],
        "design_metadata":{"source":{"kind":"platform_controlled_experimental"},"run_input":{"dataset_ref":"approved-data"}}}
    return environment,payload


def workflow(saved):
    return {"name":saved["name"],"solution_id":saved["id"],"expected_updated_at":saved["updated_at"],
        "nodes":[{"node_id":n["id"],"service_id":n["data"]["service"]["id"],"container_name":"registry","operation_name":"registry",
            "configuration":n["data"]["configuration"],"operation_contract":n["data"]["operation_contract"]} for n in saved["nodes"]],
        "edges":[{"source":e["source"],"target":e["target"],"binding":e["data"]["binding"]} for e in saved["edges"]],
        "run_input":{"dataset_ref":"approved-data"}}


def test_bound_save_reload_copy_compile_and_parameter_edits(chained):
    client,payload=chained
    r=client.post("/solutions",json=payload);assert r.status_code==200,r.text
    saved=client.get("/solutions/"+r.json()["id"]).json()
    copied=client.post("/solutions",json={k:deepcopy(saved[k]) for k in ("name","nodes","edges","design_metadata")})
    assert copied.status_code==200,copied.text
    assert copied.json()["id"]!=saved["id"] and copied.json()["edges"]==saved["edges"]
    request=workflow(saved);compiled=client.post("/workflows/compile",json=request)
    assert compiled.status_code==200,compiled.text
    report=compiled.json()["solution_studio_metadata"]["capability_bindings"]
    assert report["status"]=="verified" and report["bindings"][0]["source_slot"]==report["bindings"][0]["target_slot"]=="model_ref"
    instances=compiled.json()["solution_studio_metadata"]["execution_instances"]
    assert next(n for n in instances if n["instance_id"]=="generate")["input_bindings"]==["train"]
    from app.models.user import User
    from app.services.execution_submission import prepare,view
    from app.schemas.workflow_submit import WorkflowSubmitRequest
    with SessionLocal() as db:
        record=prepare(db,db.get(User,"designer"),WorkflowSubmitRequest.model_validate(request),compiled.json())
        before=view(record);identity=record.id
    changed=deepcopy(saved["nodes"])
    changed[0]["data"]["configuration"]["parameters"]={"epochs":1,"batch_size":6}
    changed[1]["data"]["configuration"]["parameters"]={"number_of_examples":20}
    r=client.put("/solutions/"+saved["id"],json={"nodes":changed,"expected_updated_at":saved["updated_at"]})
    assert r.status_code==200,r.text
    assert r.json()["edges"]==payload["edges"] and r.json()["nodes"][0]["data"]["operation_contract"]==saved["nodes"][0]["data"]["operation_contract"]
    from app.models.execution_submission import ExecutionSubmission
    with SessionLocal() as db:assert view(db.get(ExecutionSubmission,identity))==before


@pytest.mark.parametrize("failure",["reverse","missing-binding","wrong-representation","missing-dataset","version"])
def test_invalid_connections_and_missing_dataset_reject_before_dispatch(chained,failure):
    client,payload=chained
    if failure=="reverse":
        payload["edges"]=[{"id":"reverse","source":"generate","target":"train","data":{"binding":{"source_slot":"sequences","target_slot":"dataset_ref"}}}]
    if failure=="missing-binding":payload["edges"][0]["data"]={}
    if failure=="wrong-representation":
        with SessionLocal() as db:
            c=db.get(OperationContract,"pt-chain-generate-v2");d=deepcopy(c.definition)
            d["inputs"][0]["data_reference_protocols"]=["inline"];c.definition=d;db.commit()
    if failure=="version":payload["nodes"][0]["data"]["operation_contract"]["contract_version"]="0.3.0"
    response=client.post("/solutions",json=payload)
    if failure=="missing-dataset":
        assert response.status_code==200,response.text
        request=workflow(response.json());request.pop("run_input")
        response=client.post("/workflows/compile",json=request)
    assert response.status_code in (409,422),response.text
    if failure=="reverse":assert "GenerateData" in response.text and "TrainModel" in response.text and "dataset_ref" in response.text
    if failure=="missing-binding":assert "model_ref" in response.text
    if failure=="missing-dataset":assert "dataset_ref" in response.text


def test_multi_version_runtime_binding_negotiation_and_private_auth(chained,monkeypatch):
    client,payload=chained;saved=client.post("/solutions",json=payload).json()
    compiled=client.post("/workflows/compile",json=workflow(saved)).json()
    from app.services import capability_readiness
    from app.core.config import settings
    monkeypatch.setattr(settings,"orchestrator_services_api_key","server-private")
    contracts=compiled["solution_studio_metadata"]["capability_bindings"]["contracts"]
    calls=[]
    class Response:
        status_code=200
        def raise_for_status(self):pass
        def json(self):
            return {"capability_schema_version":"1.0","operations":[
                {"operation_name":c["runtime_operation_name"],"operation_identity":c["operation_identity"],
                 "contract_version":v,"binding_transport":"whole-output-v1",
                 "io_contract_sha256":c["definition_sha256"]} for c in contracts.values() for v in ("0.1.0","0.2.0")]}
    def get(*args,**kwargs):calls.append(kwargs);return Response()
    monkeypatch.setattr(capability_readiness.requests,"get",get)
    assert capability_readiness.require_binding_transport(compiled)["status"]=="ready"
    assert all(c["headers"]=={"Authorization":"Bearer server-private"} for c in calls)
    assert "services_api_key" not in compiled


def test_wrong_owner_cannot_read_or_copy_private_design(chained):
    client,payload=chained;saved=client.post("/solutions",json=payload).json()
    from app.main import app
    from app.dependencies.auth import get_current_user
    from app.models.user import User
    with SessionLocal() as db:
        app.dependency_overrides[get_current_user]=lambda:db.get(User,"other")
        assert client.get("/solutions/"+saved["id"]).status_code==403
    app.dependency_overrides.pop(get_current_user)
