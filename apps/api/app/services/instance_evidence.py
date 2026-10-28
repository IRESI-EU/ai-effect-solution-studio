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
            results.extend({"instance_id": n["instance_id"], "state": "unavailable", "message": "Upstream evidence unavailable"} for n in pending)
            break
        for node in ready:
            pending.remove(node)
            identity = {k: node[k] for k in ("instance_id", "task_id", "operation_name")}
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
    return {"state": state, "instances": results, "limitations": "Isolated software instrumentation; production compatibility unverified"}


def load_qualification(row, db):
    """Reuse validated Dutch collection; never relabel a submission as consumption."""
    from app.models.deployment import Deployment
    from app.services import local_dutch_capture as capture
    from app.services.orchestrator_adapter import get_workflow_status, get_workflow_tasks
    from fastapi import HTTPException
    if not capture.qualification_enabled() or db is None:
        return {"state": "unavailable", "instances": []}
    deployment = db.query(Deployment).filter(Deployment.workflow_id == row.workflow_id).first()
    if not deployment or deployment.created_by_user_id != row.owner_user_id:
        return {"state": "unavailable", "instances": []}
    try:
        collected = capture.collect(db, deployment, get_workflow_status(row.workflow_id), get_workflow_tasks(row.workflow_id)["tasks"])
        if collected is None:
            return {"state": "unavailable", "instances": []}
        evidence, blobs = collected
        instances = []
        for node in row.submitted["compiled"]["solution_studio_metadata"]["execution_instances"]:
            source = node["operation_name"] == "ConfigureAndSynthesize"
            key = "grid" if source else "benchmark"
            artifact = next((a for a in evidence["artifacts"] if a["id"] == key), {})
            available = evidence["state"] == "available" and artifact.get("state") == "available"
            instances.append({"instance_id": node["instance_id"], "task_id": node["task_id"],
                "state": "available" if available else "unavailable",
                "algorithm_consumed": evidence.get("algorithm_consumed") if source and available else None,
                "instrumentation": "Observed PowerGridGenerator seed and returned grid; verified captured configuration" if source else "Benchmark consumed the associated upstream manifest and grid digest",
                "output_sha256": artifact.get("sha256"), "input_binding_verified": bool(evidence.get("verified_bindings")) if available else False})
        return {"state": evidence["state"], "instances": instances,
                "limitations": "Isolated Dutch software workflow. Production compatibility unverified."}
    except (HTTPException, KeyError):
        return {"state": "unavailable", "instances": [], "message": "Runtime or associated evidence unavailable"}
