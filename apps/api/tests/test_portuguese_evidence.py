"""OFFLINE evidence-file fixtures; no real model, networking or concurrency claim."""
from copy import deepcopy
import base64
import hashlib
import hmac
import json
from pathlib import Path
import sqlite3
import pytest

from app.db import SessionLocal
from app.models.deployment import Deployment
from app.models.execution_submission import ExecutionSubmission
from app.models.user import User
from app.schemas.workflow_submit import WorkflowSubmitRequest
from app.services.execution_submission import prepare
from app.services import portuguese_evidence as evidence
from app.core.config import settings
from test_portuguese_chain import chained,workflow

WF="wf-cccccccccccc"


@pytest.fixture
def captured(chained,tmp_path,monkeypatch,request):
    client,payload=chained
    payload["nodes"][0]["data"]["configuration"]["parameters"]["batch_size"]=getattr(request,"param",4)
    saved=client.post("/solutions",json=payload).json()
    request=workflow(saved)
    compiled=client.post("/workflows/compile",json=request).json()
    with SessionLocal() as db:
        row=prepare(db,db.get(User,"designer"),WorkflowSubmitRequest.model_validate(request),compiled)
        row.workflow_id=WF;row.phase="submitted"
        db.add(Deployment(id="pt-result",workflow_id=WF,solution_id=saved["id"],created_by_user_id="designer",name="offline chain"))
        db.commit();sid=row.id
    monkeypatch.setattr(settings,"database_url","postgresql+psycopg://fixture:fixture@unused/pt_parameter_sandbox")
    monkeypatch.setattr(settings,"portuguese_evidence_owner_id","designer")
    monkeypatch.setattr(settings,"orchestrator_services_api_key","x"*40)
    monkeypatch.setattr(settings,"portuguese_evidence_root",str(tmp_path/"records"))
    monkeypatch.setattr(settings,"portuguese_model_root",str(tmp_path/"models"))
    monkeypatch.setattr(settings,"aie37_qualification",False)
    monkeypatch.setattr(settings,"design_ai_dutch_demo",False)
    root=Path(settings.portuguese_evidence_root);root.mkdir()
    dataset=b"datetime,value\n"+b"2026-01-01,1\n"*400;(root/"dataset.csv").write_bytes(dataset)
    nodes={n["operation_name"]:n for n in compiled["solution_studio_metadata"]["execution_instances"]}
    train=nodes["TrainModel"];gen=nodes["GenerateData"]
    producer=evidence.job_id(WF,train["task_id"])
    user="sandbox_"+hashlib.sha256(b"designer").hexdigest()[:20]
    name="model_"+producer[:32];model_bytes=b"offline trusted model fixture"
    modelpath=Path(settings.portuguese_model_root)/user/name/"model.pt";modelpath.parent.mkdir(parents=True);modelpath.write_bytes(model_bytes)
    model={"producer_workflow_id":WF,"producer_task_id":train["task_id"],"owner_id":"designer","user_id":user,
        "model_identity":name,"model_ref":"pt-model-"+producer,"model_sha256":hashlib.sha256(model_bytes).hexdigest(),
        "configuration":{"epochs":2,"batch_size":4,"max_sequence_len":100,"sample_len":1}}
    policy={"authorization_id":"offline-phase","owner_id":"designer","dataset_sha256":hashlib.sha256(dataset).hexdigest(),
        "tasks":{n["task_id"]:{"configuration":n["configuration"]} for n in nodes.values()},
        "binding":{"producer_task":train["task_id"],"consumer_task":gen["task_id"]}}
    d=sqlite3.connect(root/"journal.sqlite3")
    d.executescript("CREATE TABLE jobs(id TEXT,state TEXT,result TEXT,request TEXT); CREATE TABLE authorizations(id TEXT,policy TEXT,policy_sha256 TEXT,state TEXT,workflow_id TEXT); CREATE TABLE authorized_jobs(job_id TEXT,authorization_id TEXT,method TEXT);")
    d.execute("INSERT INTO authorizations VALUES(?,?,?,?,?)",("offline-phase",evidence.canonical(policy),evidence.digest(policy),"closed",WF))
    outputs={}
    proofs={}
    for method in ("TrainModel","GenerateData"):
        node=nodes[method];job=evidence.job_id(WF,node["task_id"])
        output=json.dumps({"model_ref":model["model_ref"]}).encode() if method=="TrainModel" else (
            "datetime,value,example\n"+"".join(f"2026-01-01,1,{e}\n" for e in range(1,11) for _ in range(100))).encode()
        fmt="json" if method=="TrainModel" else "csv";(root/(job+"."+fmt)).write_bytes(output)
        ref={"protocol":"http","format":fmt,"uri":"http://adapter/control/data/"+job}
        inputs=compiled["inputs"] if method=="TrainModel" else [outputs["TrainModel"]["output"]]
        proof={"evidence_schema_version":"2.0","authorization_id":"offline-phase","authorization_policy_sha256":evidence.digest(policy),
            "owner_id":"designer","workflow_id":WF,"task_id":node["task_id"],"instance_id":node["instance_id"],"operation_name":method,
            "configuration":node["configuration"],"inputs":evidence.core(inputs),"requested_effective":node["configuration"]["parameters"],
            "terminal_state":"complete","upstream_completion":True,"model":model,
            "sha256":hashlib.sha256(output).hexdigest(),"bytes":len(output),"output":ref,
            "algorithm_consumed":{"epochs":2,"batch_size":4} if method=="TrainModel" else {"number_of_examples":10}}
        if method=="GenerateData":proof.update(producer_output_sha256=outputs["TrainModel"]["sha256"],input_binding_verified=True,
            upstream_arguments={"model_name":name,"user_id":user})
        proof["signature"]=hmac.new(b"x"*40,evidence.canonical(proof).encode(),hashlib.sha256).hexdigest()
        (root/(job+".evidence.json")).write_text(evidence.canonical(proof))
        req={"method":method,"workflow_id":WF,"task_id":node["task_id"],"configuration":node["configuration"],"inputs":inputs}
        d.execute("INSERT INTO jobs VALUES(?,?,?,?)",(job,"complete",evidence.canonical(proof),json.dumps(req)))
        d.execute("INSERT INTO authorized_jobs VALUES(?,?,?)",(job,"offline-phase",method))
        outputs[method]=proof;proofs[method]=(job,proof)
    d.commit();d.close()
    return {"client":client,"sid":sid,"modelpath":modelpath,"root":root,"proofs":proofs,"saved":saved}


def test_historical_reader_verifies_each_instance_and_model_binding_without_network(captured,monkeypatch):
    import requests
    monkeypatch.setattr(requests,"get",lambda *a,**k:pytest.fail("Historical evidence must not contact runtime"))
    response=captured["client"].get("/workflows/"+WF+"/instance-evidence")
    assert response.status_code==200,response.text
    body=response.json();assert body["state"]=="available",body
    train,gen=body["instances"]
    assert train["algorithm_consumed"]=={"epochs":2,"batch_size":4}
    assert gen["algorithm_consumed"]=={"number_of_examples":10}
    assert gen["input_binding_verified"] and gen["summary"]["csv_rows"]==1000
    assert gen["model_binding"]["producer_task_id"]==captured["proofs"]["TrainModel"][1]["task_id"]
    assert body["historical"] and "without a live runtime" in body["observation_source"]


@pytest.mark.parametrize("failure",["output-corrupt","model-corrupt","model-missing","signature","wrong-task","wrong-workflow","wrong-owner","wrong-producer","wrong-input","unknown-schema"])
def test_invalid_or_unavailable_evidence_never_verifies_every_instance(captured,failure):
    root=captured["root"]
    if failure=="model-corrupt":captured["modelpath"].write_bytes(b"changed")
    elif failure=="model-missing":captured["modelpath"].unlink()
    elif failure=="output-corrupt":(root/(captured["proofs"]["GenerateData"][0]+".csv")).write_text("corrupt")
    else:
        job,proof=captured["proofs"]["GenerateData"];proof=deepcopy(proof)
        if failure=="signature":proof["signature"]="0"*64
        else:
            proof.pop("signature")
            if failure=="wrong-task":proof["task_id"]="task_ffffffff"
            if failure=="wrong-workflow":proof["workflow_id"]="wf-ffffffffffff"
            if failure=="wrong-owner":proof["owner_id"]="other"
            if failure=="wrong-producer":proof["model"]["producer_task_id"]="task_ffffffff"
            if failure=="wrong-input":proof["inputs"]=[{"protocol":"http","format":"json","uri":"http://elsewhere/model"}]
            if failure=="unknown-schema":proof["evidence_schema_version"]="99"
            proof["signature"]=hmac.new(b"x"*40,evidence.canonical(proof).encode(),hashlib.sha256).hexdigest()
        (root/(job+".evidence.json")).write_text(evidence.canonical(proof))
        with sqlite3.connect(root/"journal.sqlite3") as d:d.execute("UPDATE jobs SET result=? WHERE id=?",(evidence.canonical(proof),job))
    body=captured["client"].get("/workflows/"+WF+"/instance-evidence").json()
    assert body["state"]!="available" and any(v["state"]!="available" for v in body["instances"])
    if failure in {"output-corrupt","signature","wrong-task","wrong-workflow","wrong-owner","wrong-producer","wrong-input","unknown-schema"}:
        assert body["instances"][0]["state"]=="available" and body["instances"][1]["state"]=="invalid"


def test_existing_ownership_boundary_runs_before_capture(captured):
    from app.main import app
    from app.dependencies.auth import get_current_user
    with SessionLocal() as db:
        app.dependency_overrides[get_current_user]=lambda:db.get(User,"other")
        assert captured["client"].get("/workflows/"+WF+"/instance-evidence").status_code==403
    app.dependency_overrides.pop(get_current_user)


@pytest.mark.parametrize("captured",[6],indirect=True)
def test_requested_batch_size_and_observed_library_clamp_are_distinct(captured):
    body=captured["client"].get("/workflows/"+WF+"/instance-evidence").json()
    assert body["state"]=="available",body
    assert captured["saved"]["nodes"][0]["data"]["configuration"]["parameters"]["batch_size"]==6
    assert body["instances"][0]["algorithm_consumed"]["batch_size"]==4
