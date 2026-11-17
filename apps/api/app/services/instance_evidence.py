"""Read-only verification of the explicitly configured isolated proof volume."""
import base64
import hashlib
import json
from pathlib import Path
import re

from app.core.config import settings
from app.models.execution_submission import InstanceEvidenceReceipt
from sqlalchemy.exc import IntegrityError


def sha(value):
    return hashlib.sha256(value).hexdigest()


def load(row, db=None):
    if settings.portuguese_evidence_root:
        from app.services import portuguese_evidence
        return portuguese_evidence.load(row, db)
    if settings.aie37_qualification:
        return load_qualification(row, db)
    if not settings.aie18_evidence_root:
        return {"state": "unavailable", "message": "Algorithm consumption evidence is not enabled for this runtime", "instances": []}
    if not re.fullmatch(r"wf-[a-f0-9]{12}", row.workflow_id or ""):
        return {"state": "unavailable", "message": "Unsupported historical workflow identity", "instances": []}
    snapshot = row.submitted["compiled"]
    instances = snapshot["solution_studio_metadata"]["execution_instances"]
    accepted, results = {}, []
    # Verify in binding order, independent of saved node-array ordering.
    pending = list(instances)
    while pending:
        ready = [n for n in pending if all(source in accepted for source in n["input_bindings"])]
        if not ready:
            results.extend({**{key: n[key] for key in ("instance_id", "task_id", "operation_name", "node_key")}, "state": "unavailable", "message": "Upstream evidence unavailable"} for n in pending)
            break
        for node in ready:
            pending.remove(node)
            identity = {k: node[k] for k in ("instance_id", "task_id", "operation_name", "node_key")}
            role = {"ConfigureAndSynthesize": "synth", "GenerateTopology": "topology"}.get(node["operation_name"])
            if not role or not node["configuration"] or not re.fullmatch(r"task_[a-f0-9]{8}", node["task_id"]):
                results.append({**identity, "state": "unavailable", "message": "No supported consumption recorder for this operation"})
                continue
            try:
                directory = Path(settings.aie18_evidence_root) / role / row.workflow_id / node["task_id"]
                # No request-derived paths or symlinks may leave the read-only root.
                root = Path(settings.aie18_evidence_root).resolve()
                def read(name):
                    path = (directory / name).resolve()
                    if not path.is_relative_to(root) or path.stat().st_size > 5000000:
                        raise ValueError("Invalid evidence path or size")
                    return path.read_bytes()
                manifest_raw = read("manifest.json")
                receipt = db.get(InstanceEvidenceReceipt, (row.id, node["task_id"])) if db is not None else None
                if receipt is not None and receipt.manifest_sha256 != sha(manifest_raw):
                    raise ValueError("Previously recorded evidence changed")
                manifest = json.loads(manifest_raw)
                request_raw, output_raw = read("request.json"), read("output.json")
                request, output = json.loads(request_raw), json.loads(output_raw)
                config = node["configuration"]
                if (manifest["workflow_id"] != row.workflow_id or manifest["task_id"] != node["task_id"]
                    or manifest["instance_id"] != node["instance_id"] or manifest["operation"] != node["operation_name"]
                    or manifest["contract"] != config or manifest["algorithm_consumed"] != config["parameters"]
                    or manifest["wrapper_received"] != config["parameters"]
                    or manifest["request_sha256"] != sha(request_raw) or manifest["output_sha256"] != sha(output_raw)
                    or request["workflow_id"] != row.workflow_id or request["task_id"] != node["task_id"]
                    or request["method"] != node["operation_name"] or request["configuration"] != config):
                    raise ValueError("Execution configuration or artifact association mismatch")
                refs = [accepted[source]["output_ref"] for source in node["input_bindings"]] if node["input_bindings"] else snapshot.get("inputs", [])
                def core(references):
                    return [{k: r[k] for k in ("protocol", "uri", "format")} for r in references]
                if core(request["inputs"]) != core(refs):
                    raise ValueError("Execution input bindings differ from the immutable submission")
                if db is not None and receipt is None:
                    db.add(InstanceEvidenceReceipt(submission_id=row.id, task_id=node["task_id"], manifest_sha256=sha(manifest_raw)))
                    try:
                        db.commit()
                    except IntegrityError:
                        db.rollback()
                        receipt = db.get(InstanceEvidenceReceipt, (row.id, node["task_id"]))
                        if receipt is None or receipt.manifest_sha256 != sha(manifest_raw):
                            raise ValueError("Concurrent evidence receipt mismatch")
                accepted[node["instance_id"]] = {"output_ref": {"protocol": "inline", "format": "json", "uri": base64.b64encode(output_raw).decode()}}
                results.append({**identity, "state": "available", "wrapper_received": manifest["wrapper_received"],
                    "algorithm_consumed": manifest["algorithm_consumed"], "instrumentation": manifest["instrumentation"],
                    "manifest_sha256": sha(manifest_raw), "request_sha256": sha(request_raw), "output_sha256": sha(output_raw),
                    "wrapper_sha256": manifest["wrapper_sha256"], "contracts_sha256": manifest["contracts_sha256"],
                    "summary": {"topology_count": output.get("topology_count"), "grid_seed": output.get("grid_data", {}).get("seed")}})
            except FileNotFoundError:
                results.append({**identity, "state": "pending", "message": "No completed algorithm evidence recorded"})
            except (OSError, ValueError, KeyError, TypeError):
                results.append({**identity, "state": "unavailable", "message": "Algorithm evidence failed integrity or association validation"})
    state = "available" if results and all(r["state"] == "available" for r in results) else "unavailable"
    return {"state": state, "workflow_id": row.workflow_id, "submission_id": row.id, "instances": results, "limitations": "Isolated software instrumentation; production compatibility unverified"}


def load_qualification(row, db):
    """Project per-instance verdicts from the same validated qualified capture."""
    from app.models.deployment import Deployment
    from app.models.local_dutch_execution import LocalDutchExecution
    from app.schemas.workflow_submit import WorkflowSubmitRequest
    from app.services import local_dutch_capture as capture, qualified_demo
    from app.services.dutch_capture_contract import NODE_KEYS, task_id
    base = {"workflow_id": row.workflow_id, "submission_id": row.id,
        "source": capture.EVIDENCE_SOURCE, "historical": True}
    def unavailable(message, state="unavailable"):
        return {**base, "state": state, "message": message, "instances": []}
    if db is None or not capture.enabled() or not (capture.qualification_enabled() or qualified_demo.profile_enabled()):
        return unavailable("Qualified capture inspection is not enabled for this profile.")
    deployment = db.query(Deployment).filter(Deployment.workflow_id == row.workflow_id).first()
    record = db.query(LocalDutchExecution).filter(LocalDutchExecution.workflow_id == row.workflow_id).first()
    if (not deployment or not record or deployment.created_by_user_id != row.owner_user_id
        or record.owner_user_id != row.owner_user_id or deployment.solution_id != row.solution_id or record.solution_id != row.solution_id):
        return unavailable("The capture is not associated with this owned submission.", "conflicting")
    try:
        snapshot, compiled = record.submitted, row.submitted["compiled"]
        normalize = lambda value: WorkflowSubmitRequest.model_validate(value).model_dump(mode="json", exclude={"submission_id"})
        if (("authorization" in row.submitted and snapshot["request"].get("submission_id") != row.id)
            or snapshot["request"].get("submission_id") not in (None, row.id)
            or normalize(snapshot["request"]) != normalize(row.submitted["request"])
            or any(snapshot[key] != compiled[key] for key in ("blueprint", "dockerinfo", "task_configurations"))
            or snapshot["capability_bindings"] != compiled["solution_studio_metadata"]["capability_bindings"]):
            return unavailable("Capture and submitted execution snapshots conflict.", "conflicting")
        nodes = compiled["solution_studio_metadata"]["execution_instances"]
        if len(nodes) != 2 or len({node["instance_id"] for node in nodes}) != 2:
            return unavailable("Recorded instance identities are ambiguous.", "conflicting")
        workflow, tasks, live, observation_source = capture.associated_state(db, deployment)
        collected = capture.collect(db, deployment, workflow, tasks, runtime_live=live)
        if collected is None:
            return unavailable("No qualified capture is associated with this run.")
        evidence, _ = collected
        instances = []
        source = next((node for node in nodes if node["node_key"] == NODE_KEYS["synth"]), None)
        for node in nodes:
            identity = {key: node[key] for key in ("instance_id", "task_id", "node_key", "operation_name")}
            role = next((role for role, key in NODE_KEYS.items() if key == node["node_key"]), None)
            requested = next((n for n in row.submitted["request"]["nodes"] if n["node_id"] == node["instance_id"]), None)
            bindings = snapshot["capability_bindings"].get("bindings", [])
            matches = (role is not None and node["task_id"] == task_id(role)
                and node["operation_name"] == NODE_KEYS[role].split(":")[1]
                and node.get("configuration") == snapshot["task_configurations"].get(node["node_key"])
                and requested and requested["operation_name"] == node["operation_name"]
                and requested["service_id"] == node["service_id"])
            if role == "synth":
                matches = matches and node["configuration"]["instance_id"] == node["instance_id"] and not node["input_bindings"]
            elif role == "benchmark":
                matches = (matches and source and node["input_bindings"] == [source["instance_id"]]
                    and len(bindings) == 1 and bindings[0]["source"] == source["instance_id"]
                    and bindings[0]["target"] == node["instance_id"])
            proof = evidence.get("roles", {}).get(role, {})
            if not matches or proof.get("task_id") != node["task_id"] or proof.get("node_key") != node["node_key"] or proof.get("workflow_id") != row.workflow_id:
                instances.append({**identity, "state": "conflicting", "message": "Instance, operation, task or input binding differs from the recorded capture."})
                continue
            instances.append({**identity, **proof,
                "instrumentation": "Observed generator seed, validated configuration and returned grid." if role == "synth" else
                    "Validated benchmark input reference, upstream manifest and grid digest."})
        state = "available" if instances and all(item["state"] == "available" for item in instances) else evidence["state"]
        if state == "available" and any(item["state"] != "available" for item in instances):
            state = "conflicting"
        return {**base, "state": state, "instances": instances, "observation_source": observation_source,
            "message": evidence["message"], "limitations": evidence["limitations"]}
    except (ValueError, KeyError, TypeError, AttributeError):
        return unavailable("Recorded capture or submission metadata is invalid.", "invalid")
