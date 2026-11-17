"""Explicit operator steps for the sole new chained phase. No retries or daemon.
Set PT_SANDBOX_PROFILE to the retained profile and PT_SANDBOX_RECORDS to the new
private record directory. Each mutating step has an exclusive durable marker.
"""
import argparse
import base64
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import requests

PROFILE=Path(os.environ["PT_SANDBOX_PROFILE"]).resolve()
RECORDS=Path(os.environ["PT_SANDBOX_RECORDS"]).resolve()
C=["docker","--context","desktop-linux","compose","-f",str(PROFILE/"compose.private.json")]
D=["docker","--context","desktop-linux"]
BASE="http://127.0.0.1:23124/api"
SCOPE="pt-chain-20261113-01"
ACTOR="as-via-Codex/user-authorized-20261113"
CONTAINER="ai-effect-pt-chain-20261113-worker"


def session():
    s=requests.Session();s.trust_env=False
    credential=json.loads((PROFILE/"credentials.json").read_text())
    r=s.post(BASE+"/auth/login",json={k:credential[k] for k in ("email","password")},timeout=15)
    r.raise_for_status()
    if r.json()["id"]!=credential["owner_id"]:raise ValueError("Designer identity differs")
    return s


def api(s,method,path,**kwargs):
    r=s.request(method,BASE+path,timeout=30,**kwargs)
    if not r.ok:raise RuntimeError(str(r.status_code)+" "+r.text[:1500])
    return r.json()


def write_new(name,value):
    with (RECORDS/name).open("x") as f:json.dump(value,f,indent=2)


def command(args,timeout=30):
    return subprocess.check_output(args,text=True,timeout=timeout)


def journal_operator(action,*args):
    out=command(C+["run","--rm","--no-deps","chain-operator",action,*args,"--actor",ACTOR])
    value=json.loads(out)
    (RECORDS/("authorization-"+action+".private.json")).write_text(json.dumps(value,indent=2))
    return value


def preservation(s):
    before=json.loads((RECORDS/"owner-designs-before.private.json").read_text())
    for record in before:
        if api(s,"GET","/solutions/"+record["saved"]["id"])!=record["saved"]:
            raise ValueError("A preserved owner or historical design changed")
    baseline=json.loads((RECORDS/"journal-before.private.json").read_text())
    code="import sqlite3,json; d=sqlite3.connect('file:/state/journal.sqlite3?mode=ro',uri=True); d.row_factory=sqlite3.Row; print(json.dumps({'jobs':[dict(r) for r in d.execute('select * from jobs')],'models':[dict(r) for r in d.execute('select * from models')]}))"
    current=json.loads(command(C+["exec","-T","pt-adapter","python","-c",code]))
    prior={r["id"]:r for r in baseline["jobs"]}
    if any(next((r for r in current["jobs"] if r["id"]==k),None)!=v for k,v in prior.items()) or current["models"]!=baseline["models"]:
        raise ValueError("Historical journal jobs or standalone model mapping changed")
    return {"preserved_solutions":len(before),"legacy_jobs":len(prior),"total_jobs":len(current["jobs"])}


def queues():
    script="local r={}; for _,k in ipairs(redis.call('KEYS','*')) do local t=redis.call('TYPE',k).ok; if t=='list' then table.insert(r,{k,redis.call('LLEN',k)}) elseif string.match(k,'^workflow:[^:]+$') then table.insert(r,{k,redis.call('GET',k)}) end end; return cjson.encode(r)"
    return json.loads(command(C+["exec","-T","redis","redis-cli","EVAL",script,"0"]))


def prepare():
    s=session();preservation(s)
    contracts={}
    for method in ("TrainModel","GenerateData"):
        sid="pt-experimental-chain-"+method
        value=api(s,"GET","/services/"+sid+"/operation-contract-resolution")["contract"]
        if value["contract_version"]!="0.2.0" or value["definition"]["binding_transport"]!="whole-output-v1":
            raise ValueError("Published chain contract differs")
        contracts[method]=value
    nodes=[{"id":"input","type":"input","position":{"x":80,"y":180},"data":{"label":"Authorized dataset input","node_kind":"workflow_input"}}]
    for method,x in (("TrainModel",330),("GenerateData",620)):
        c=contracts[method]
        service=api(s,"GET","/services/"+c["service_id"])
        nodes.append({"id":"pt-chain-train" if method=="TrainModel" else "pt-chain-generate","position":{"x":x,"y":180},
            "data":{"node_kind":"service","label":method,"service":service,"operation_contract":{"contract_id":c["id"],"contract_version":"0.2.0"},
                "configuration":{"contract_id":c["id"],"contract_version":"0.2.0",
                    "parameters":{"epochs":2,"batch_size":4} if method=="TrainModel" else {"number_of_examples":10}}}})
    nodes.append({"id":"output","type":"output","position":{"x":910,"y":180},"data":{"label":"Generated CSV sequences","node_kind":"workflow_output"}})
    payload={"name":"EXPERIMENTAL Portuguese TrainModel → GenerateData",
        "description":"Separate corrected review copy. Guarded synthetic model handoff; not partner-approved or scientifically qualified.",
        "nodes":nodes,"edges":[{"id":"dataset-train","source":"input","target":"pt-chain-train"},
            {"id":"model-handoff","source":"pt-chain-train","target":"pt-chain-generate","data":{"binding":{"source_slot":"model_ref","target_slot":"model_ref"}}},
            {"id":"generated-output","source":"pt-chain-generate","target":"output"}],
        "design_metadata":{"source":{"kind":"platform_controlled_experimental"},"run_input":{"dataset_ref":"pt-approved-synthetic-data"},
            "preserved_owner_design_id":"0fe46709-e564-4a82-b9f2-a7d6d94a8483"}}
    if (RECORDS/"corrected-design.private.json").exists():raise ValueError("Corrected design already exists; do not duplicate")
    saved=api(s,"POST","/solutions",json=payload);write_new("corrected-design.private.json",saved)
    print(json.dumps({"builder_url":"http://127.0.0.1:23124/builder?solutionId="+saved["id"],"submitted":False}))


def request(saved):
    nodes=[n for n in saved["nodes"] if n.get("data",{}).get("service")];ids={n["id"] for n in nodes}
    return {"name":saved["name"],"solution_id":saved["id"],"expected_updated_at":saved["updated_at"],
        "nodes":[{"node_id":n["id"],"service_id":n["data"]["service"]["id"],"container_name":n["data"]["service"]["container_name"],
            "operation_name":n["data"]["service"]["operation_name"],"configuration":n["data"]["configuration"],
            "operation_contract":n["data"]["operation_contract"]} for n in nodes],
        "edges":[{"source":e["source"],"target":e["target"],"binding":e["data"]["binding"]} for e in saved["edges"] if e["source"] in ids and e["target"] in ids],
        "run_input":saved["design_metadata"]["run_input"]}


def snapshot():
    s=session();kept=preservation(s)
    stored=json.loads((RECORDS/"corrected-design.private.json").read_text())
    saved=api(s,"GET","/solutions/"+stored["id"]);body=request(saved)
    expected={"TrainModel":{"epochs":2,"batch_size":4},"GenerateData":{"number_of_examples":10}}
    if {n["operation_name"]:n["configuration"]["parameters"] for n in body["nodes"]}!=expected:raise ValueError("Authorized settings differ")
    compiled=api(s,"POST","/workflows/compile",json=body);ready=api(s,"POST","/workflows/runtime-preflight",json=body)
    if ready["status"]!="ready":raise ValueError("Runtime readiness failed")
    config=json.loads((PROFILE/"compose.private.json").read_text())
    containers=command(C+["ps","--all","--format","json"])
    (RECORDS/"containers-before-dispatch.private.jsonl").write_text(containers)
    ml=json.loads(command(D+["inspect","ai-effect-pt-parameters-ml-1"]))[0]
    if ml["HostConfig"]["Memory"]!=3*1024**3 or ml["HostConfig"]["NanoCpus"]!=2_000_000_000:
        raise ValueError("Actual ML resource limits differ")
    if json.loads(command(D+["inspect","ai-effect-pt-parameters-worker-1"]))[0]["State"]["Running"]:
        raise ValueError("Old daemon must remain stopped")
    q=queues()
    if any(isinstance(v[1],int) and v[1] for v in q):raise ValueError("Unresolved queued work; do not start any worker")
    for k,v in q:
        if isinstance(v,str) and json.loads(v)["status"] not in ("completed","failed"):
            raise ValueError("Unapproved nonterminal workflow exists; preserve it and stop")
    policy=json.loads((PROFILE/"policy.json").read_text())
    nodes=compiled["solution_studio_metadata"]["execution_instances"]
    training=next(n for n in nodes if n["operation_name"]=="TrainModel")
    generation=next(n for n in nodes if n["operation_name"]=="GenerateData")
    sha=hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest()
    resources={"ml":{"cpus":config["services"]["ml"]["cpus"],"mem_limit":config["services"]["ml"]["mem_limit"],
        "image":ml["Image"],"sequence_len":100,"dataset_rows":400},
        "images":{k:v["image"] for k,v in config["services"].items() if k in {"api","web","pt-adapter","model-observer","orchestrator","chain-worker"}}}
    grant={"schema_version":"pt-chain-authorization-v1","authorization_id":SCOPE,"owner_id":policy["owner_id"],
        "actor":ACTOR,"reason":"User-authorized single combined phase 2026-11-13; preserve exhausted previous scope",
        "request_sha256":sha,"dataset_sha256":policy["dataset_sha256"],"resources":resources,
        "tasks":{n["task_id"]:{"method":n["operation_name"],"configuration":n["configuration"],
            "inputs":compiled["inputs"] if n["operation_name"]=="TrainModel" else "producer:model_ref"} for n in nodes},
        "binding":{"producer_task":training["task_id"],"consumer_task":generation["task_id"],"source_slot":"model_ref","target_slot":"model_ref"}}
    write_new("snapshot.private.json",{"saved":saved,"request":body,"compiled":compiled,"readiness":ready,
        "resources":resources,"queues":q,"preservation":kept,"request_sha256":sha})
    write_new("authorization.private.json",grant)
    print(json.dumps({"snapshot":"frozen","request_sha256":sha,"resources":resources,"workflow_submissions":0}))


def authorize():
    value=journal_operator("create","--file","/review/authorization.json")
    print(json.dumps({"authorization":SCOPE,"state":"prepared","legacy_jobs":value["legacy_jobs"],"scoped_jobs":len(value["scoped_jobs"])}))


def submit():
    s=session();snapshot=json.loads((RECORDS/"snapshot.private.json").read_text())
    if api(s,"GET","/solutions/"+snapshot["saved"]["id"])!=snapshot["saved"]:raise ValueError("Saved design drift; stop")
    preservation(s)
    state=journal_operator("status")
    scope=next(v for v in state["authorizations"] if v["id"]==SCOPE)
    if scope["state"]!="prepared" or scope["workflow_id"] is not None:raise ValueError("Authorization is not fresh")
    write_new("submission-attempt.private.json",{"state":"dispatching","request_sha256":snapshot["request_sha256"]})
    # Exactly one request; unknown outcome leaves the marker consumed.
    result=api(s,"POST","/workflows/submit-to-orchestrator",json=snapshot["request"])
    write_new("submission-response.private.json",result)
    journal_operator("bind","--id",SCOPE,"--workflow",result["workflow_id"],"--request-sha256",snapshot["request_sha256"])
    print(json.dumps({"workflow_id":result["workflow_id"],"submission_id":result["submission_id"],"worker_started":False}))


def start_worker():
    response=json.loads((RECORDS/"submission-response.private.json").read_text());wf=response["workflow_id"]
    state=journal_operator("status");scope=next(v for v in state["authorizations"] if v["id"]==SCOPE)
    if scope["workflow_id"]!=wf or scope["state"]!="active":raise ValueError("Exact workflow authority missing")
    if json.loads(command(D+["inspect","ai-effect-pt-parameters-worker-1"]))[0]["State"]["Running"]:raise ValueError("Old daemon running")
    write_new("worker-attempt.private.json",{"workflow_id":wf,"container":CONTAINER,"authority":SCOPE,"queues_before":queues()})
    identity=command(C+["run","-d","--name",CONTAINER,"--no-deps","chain-worker","python","worker_cli.py",wf,"--timeout","1","--poll-interval","1"]).strip()
    print(json.dumps({"targeted_worker":identity,"only_workflow":wf}))


def observe():
    response=json.loads((RECORDS/"submission-response.private.json").read_text());wf=response["workflow_id"];s=session()
    result={"workflow":api(s,"GET","/orchestrator/workflows/"+wf),"tasks":api(s,"GET","/orchestrator/workflows/"+wf+"/tasks"),
        "submission":api(s,"GET","/workflows/"+wf+"/submitted-configuration"),"evidence":api(s,"GET","/workflows/"+wf+"/instance-evidence"),
        "preservation":preservation(s)}
    (RECORDS/"observed.private.json").write_text(json.dumps(result,indent=2))
    print(json.dumps({"workflow":result["workflow"],"tasks":[{k:t[k] for k in ("task_id","node_key","status","error")} for t in result["tasks"]["tasks"]],
        "evidence":result["evidence"],"preservation":result["preservation"]}))


def close():
    value=json.loads((RECORDS/"observed.private.json").read_text())
    if value["workflow"]["status"]!="completed" or value["evidence"]["state"]!="available" or any(t["status"]!="completed" for t in value["tasks"]["tasks"]):
        raise ValueError("Acceptance did not pass; preserve failure, stop worker and close via explicit operator without retry")
    worker=json.loads(command(D+["inspect",CONTAINER]))[0]
    if worker["State"]["Running"]:raise ValueError("Targeted worker is not yet stopped")
    if any(isinstance(v[1],int) and v[1] for v in queues()):raise ValueError("Queue is not empty; do not dispatch unrelated work")
    state=journal_operator("close","--id",SCOPE)
    (RECORDS/"completion.private.json").write_text(json.dumps({"scope":state,"worker_exit":worker["State"]["ExitCode"],"queues":queues()},indent=2))
    print(json.dumps({"authorization":SCOPE,"state":"closed","worker":"stopped","legacy_jobs":state["legacy_jobs"],"new_jobs":len(state["scoped_jobs"])}))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("action",choices=["prepare","snapshot","authorize","submit","start_worker","observe","close"])
    a=p.parse_args();globals()[a.action]()
