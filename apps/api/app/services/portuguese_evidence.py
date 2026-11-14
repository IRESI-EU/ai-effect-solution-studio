"""Read-only Portuguese v2 evidence. No runtime request, arbitrary file or draft read."""
import csv
import hashlib
import hmac
import io
import json
from pathlib import Path
import re
import sqlite3

from app.core.config import settings
from app.models.deployment import Deployment
from app.services.execution_submission import view


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def job_id(workflow,task):
    return hashlib.sha256(json.dumps([workflow,task]).encode()).hexdigest()


def core(refs):
    return [{k:r[k] for k in ("protocol","uri","format")} for r in refs]


def read(root,relative,limit):
    root=Path(root).resolve();path=(root/relative).resolve()
    if not path.is_relative_to(root) or path.stat().st_size>limit:
        raise ValueError("Evidence path/size is invalid")
    return path.read_bytes()


def csv_counts(data,expected):
    counts={}
    for row in csv.DictReader(io.StringIO(data.decode())):
        key=row["example"]
        counts[key]=counts.get(key,0)+1
    if set(counts)!={str(i) for i in range(1,expected+1)} or set(counts.values())!={100}:
        raise ValueError("CSV sequence count or observation lengths differ")
    return {"generated_examples":len(counts),"csv_rows":sum(counts.values()),"observations_per_example":100}


def load(row,db):
    base={"workflow_id":row.workflow_id,"submission_id":row.id,"source":"Platform-controlled Portuguese sidecar capture v2",
        "historical":True,"observation_source":"Signed terminal adapter observation; current artifact bytes revalidated without a live runtime"}
    def unavailable(message,state="unavailable",instances=None):
        return {**base,"state":state,"message":message,"instances":instances or []}
    # Explicit sandbox scope, separate from all qualified Dutch adapters.
    from sqlalchemy.engine import make_url
    if (db is None or make_url(settings.database_url).database!="pt_parameter_sandbox"
        or settings.aie37_qualification or settings.design_ai_dutch_demo
        or not settings.portuguese_evidence_owner_id or row.owner_user_id!=settings.portuguese_evidence_owner_id
        or len(settings.orchestrator_services_api_key)<32):
        return unavailable("Portuguese experimental evidence authority does not match this profile.","inaccessible")
    deployment=db.query(Deployment).filter(Deployment.workflow_id==row.workflow_id).first()
    if (not deployment or deployment.created_by_user_id!=row.owner_user_id or deployment.solution_id!=row.solution_id):
        return unavailable("Owned deployment and immutable submission association differ.","conflicting")
    try:
        view(row)  # Revalidate immutable submission digest, never inspect its editable solution.
        compiled=row.submitted["compiled"]
        nodes=compiled["solution_studio_metadata"]["execution_instances"]
        if not re.fullmatch(r"wf-[a-f0-9]{12}",row.workflow_id or ""):
            raise ValueError("Unsupported workflow identity")
        root=Path(settings.portuguese_evidence_root).resolve()
        journal=(root/"journal.sqlite3").resolve()
        if not journal.is_relative_to(root):raise ValueError("Invalid journal path")
        connection=sqlite3.connect(journal.as_uri()+"?mode=ro",uri=True,timeout=3)
        connection.row_factory=sqlite3.Row
        with connection:
            records={r["id"]:dict(r) for r in connection.execute("SELECT * FROM jobs")}
            # Legacy records predate the additive tables and remain inspectable.
            tables={r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            authorities={r["id"]:dict(r) for r in connection.execute("SELECT * FROM authorizations")} if "authorizations" in tables else {}
            assignments={r["job_id"]:dict(r) for r in connection.execute("SELECT * FROM authorized_jobs")} if "authorized_jobs" in tables else {}
        connection.close()
    except FileNotFoundError:return unavailable("Recorded evidence storage is missing.","inaccessible")
    except (OSError,sqlite3.Error):return unavailable("Recorded evidence storage cannot be read.","inaccessible")
    except (ValueError,KeyError,TypeError):return unavailable("Immutable submission or recorded metadata is invalid.","invalid")

    accepted={};results=[];pending=list(nodes)
    while pending:
        ready=[n for n in pending if all(v in accepted for v in n["input_bindings"])]
        if not ready:
            results.extend({**{k:n[k] for k in ("instance_id","task_id","node_key","operation_name")},
                "state":"unavailable","message":"Upstream model evidence is not verified."} for n in pending)
            break
        for node in ready:
            pending.remove(node)
            identity={k:node[k] for k in ("instance_id","task_id","node_key","operation_name")}
            result={**identity,"state":"unavailable"}
            try:
                config=node["configuration"];job=job_id(row.workflow_id,node["task_id"]);record=records.get(job)
                if not config or config["operation_identity"] not in {
                    "urn:aieffect:experimental:portuguese:train-model","urn:aieffect:experimental:portuguese:generate-data"}:
                    raise ValueError("Unsupported experimental operation")
                if config["contract_version"]=="0.1.0":
                    result.update(message="Historical standalone v0.1 settings are retained; no versioned consumption capture was recorded.")
                    results.append(result);continue
                if config["contract_version"]!="0.2.0":raise ValueError("Unsupported evidence contract version")
                if not record:
                    result.update(state="pending",message="No task capture is recorded yet.");results.append(result);continue
                if record["state"]=="running":
                    result.update(state="pending",message="Task observation is not terminal.");results.append(result);continue
                if not record["result"]:raise ValueError("Terminal task capture is missing")
                proof=json.loads(record["result"]);signature=proof.pop("signature",None)
                expected=hmac.new(settings.orchestrator_services_api_key.encode(),canonical(proof).encode(),hashlib.sha256).hexdigest()
                if not isinstance(signature,str) or not hmac.compare_digest(signature,expected):
                    raise ValueError("Capture authentication differs")
                proof["signature"]=signature
                file=json.loads(read(root,job+".evidence.json",100000))
                if file!=proof:raise ValueError("Recorded capture file and journal disagree")
                authority=authorities.get(proof["authorization_id"]);assignment=assignments.get(job)
                if not authority or not assignment or assignment["authorization_id"]!=authority["id"] or assignment["method"]!=node["operation_name"]:
                    raise ValueError("Task authorization association differs")
                policy=json.loads(authority["policy"])
                if (authority["state"] not in ("active","closed") or digest(policy)!=authority["policy_sha256"] or digest(policy)!=proof["authorization_policy_sha256"]
                    or authority["workflow_id"]!=row.workflow_id or policy["owner_id"]!=row.owner_user_id
                    or policy["tasks"][node["task_id"]]["configuration"]!=config):
                    raise ValueError("Frozen authorization and submitted instance differ")
                request=json.loads(record["request"])
                if (proof["evidence_schema_version"]!="2.0" or proof["owner_id"]!=row.owner_user_id
                    or proof["workflow_id"]!=row.workflow_id or proof["task_id"]!=node["task_id"]
                    or proof["instance_id"]!=node["instance_id"] or proof["operation_name"]!=node["operation_name"]
                    or proof["configuration"]!=config or request["configuration"]!=config
                    or request["workflow_id"]!=row.workflow_id or request["task_id"]!=node["task_id"] or request["method"]!=node["operation_name"]
                    or proof["terminal_state"]!=record["state"] or core(request["inputs"])!=proof["inputs"]):
                    raise ValueError("Workflow, task, instance or configuration association differs")
                if record["state"]!="complete" or not proof["upstream_completion"]:
                    result.update(message=proof.get("error","Task failed or its outcome is uncertain; no consumption claim."))
                    results.append(result);continue
                model=proof["model"]
                producer_task=policy["binding"]["producer_task"]
                producer_job=job_id(row.workflow_id,producer_task)
                user="sandbox_"+hashlib.sha256(row.owner_user_id.encode()).hexdigest()[:20]
                name="model_"+producer_job[:32]
                if (model["producer_workflow_id"]!=row.workflow_id or model["producer_task_id"]!=producer_task
                    or model["owner_id"]!=row.owner_user_id or model["user_id"]!=user or model["model_identity"]!=name
                    or model["model_ref"]!="pt-model-"+producer_job):
                    raise ValueError("Model provenance belongs to a different producer or owner")
                model_bytes=read(settings.portuguese_model_root,user+"/"+name+"/model.pt",50*1024*1024)
                if hashlib.sha256(model_bytes).hexdigest()!=model["model_sha256"]:
                    raise ValueError("Produced model artifact integrity differs")
                fmt="json" if node["operation_name"]=="TrainModel" else "csv"
                output=read(root,job+"."+fmt,5000000)
                if hashlib.sha256(output).hexdigest()!=proof["sha256"] or len(output)!=proof["bytes"]:
                    raise ValueError("Output artifact integrity differs")
                if proof["requested_effective"]!=config["parameters"]:raise ValueError("Validated parameters differ")
                if node["operation_name"]=="TrainModel":
                    if node["input_bindings"] or core(request["inputs"])!=core(compiled["inputs"]):
                        raise ValueError("Training dataset input differs from the immutable submission")
                    dataset=read(root,"dataset.csv",1000000)
                    if hashlib.sha256(dataset).hexdigest()!=policy["dataset_sha256"]:raise ValueError("Dataset integrity differs")
                    sequences=sum(1 for _ in csv.DictReader(io.StringIO(dataset.decode())))//100
                    saved=model["configuration"];params=config["parameters"]
                    if (saved!={"epochs":params["epochs"],"batch_size":min(params["batch_size"],sequences),"max_sequence_len":100,"sample_len":1}
                        or json.loads(output)!={"model_ref":model["model_ref"]}
                        or proof["algorithm_consumed"]!={"epochs":saved["epochs"],"batch_size":saved["batch_size"]}):
                        raise ValueError("Saved model configuration or opaque reference differs")
                    consumed={"epochs":saved["epochs"],"batch_size":saved["batch_size"]}
                    summary={"training_sequences":sequences,"model_sha256":model["model_sha256"]}
                    message="Saved model configuration and artifact verified; batch size reflects the library's training-sequence clamp."
                elif node["operation_name"]=="GenerateData":
                    if len(node["input_bindings"])!=1:raise ValueError("Generation requires one producer binding")
                    producer=accepted[node["input_bindings"][0]]
                    bindings=compiled["solution_studio_metadata"]["capability_bindings"]["bindings"]
                    if (producer["task_id"]!=producer_task or producer["model"]!=model
                        or core(request["inputs"])!=core([producer["output"]])
                        or proof["producer_output_sha256"]!=producer["sha256"]
                        or policy["binding"]["consumer_task"]!=node["task_id"]
                        or not any(b["source"]==node["input_bindings"][0] and b["target"]==node["instance_id"]
                            and b["source_slot"]==b["target_slot"]=="model_ref" and b["transport"]=="whole-output-v1" for b in bindings)
                        or proof["upstream_arguments"]["model_name"]!=name or proof["upstream_arguments"]["user_id"]!=user):
                        raise ValueError("Generation did not consume this authorized producer's model")
                    summary=csv_counts(output,config["parameters"]["number_of_examples"])
                    consumed={"number_of_examples":summary["generated_examples"]}
                    if proof["algorithm_consumed"]!=consumed:raise ValueError("Observed generated sequence count differs")
                    summary["model_sha256"]=model["model_sha256"]
                    message="Consumed the model produced by TrainModel in this workflow; producer reference and model/output hashes revalidated."
                    result.update(input_binding_verified=True,model_binding={"producer_task_id":producer_task,
                        "producer_workflow_id":row.workflow_id,"model_sha256":model["model_sha256"]})
                else:raise ValueError("Unsupported operation")
                result.update(state="available",algorithm_consumed=consumed,wrapper_received=config["parameters"],
                    output_sha256=proof["sha256"],summary=summary,message=message,
                    instrumentation="Versioned signed experimental capture plus current model/output artifact hashes; no scientific-quality claim.")
                accepted[node["instance_id"]]={**proof,"task_id":node["task_id"]}
            except FileNotFoundError:result.update(message="Completed task artifact is missing; no consumption claim.")
            except PermissionError:result.update(state="inaccessible",message="Recorded artifact is inaccessible.")
            except (ValueError,KeyError,TypeError,OSError,IndexError):result.update(state="invalid",message="Experimental evidence failed integrity or producer/consumer association validation.")
            results.append(result)
    state="available" if results and all(r["state"]=="available" for r in results) else "unavailable"
    return {**base,"state":state,"instances":results,"limitations":"Platform-controlled experimental observation; scientific suitability, owner approval and hosted compatibility unverified."}
