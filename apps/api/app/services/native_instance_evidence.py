"""Inspect node instrumentation through existing owned task outputs.

No service registry, arbitrary URL fetch, or new capture subsystem. Consumed
values are node-reported algorithm arguments, checked against the immutable
submission, observed task/input references and the existing digest receipts.
"""
import base64
import hashlib
import json

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.models.deployment import Deployment
from app.models.execution_submission import InstanceEvidenceReceipt
from app.services.data_reference_service import resolve_artifact_file
from app.services.orchestrator_adapter import get_workflow_tasks
from app.services.execution_submission import view

MAX_BYTES = 5_000_000


class EvidenceUnavailable(Exception):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def core(references):
    return [{k: ref[k] for k in ("protocol", "uri", "format")} for ref in references]


def read(reference, workflow_id):
    if reference["protocol"] == "inline":
        if len(reference["uri"]) > MAX_BYTES * 2: raise EvidenceUnavailable("Input exceeds evidence limit")
        raw = base64.b64decode(reference["uri"], validate=True)
    elif reference["protocol"] == "file":
        path = resolve_artifact_file(reference["uri"])
        if path is None: raise EvidenceUnavailable("Artifact is not available in the authorized read-only volume")
        if workflow_id not in path.parts:
            raise ValueError("Artifact is outside the recorded workflow namespace")
        if path.stat().st_size > MAX_BYTES: raise EvidenceUnavailable("Artifact exceeds evidence limit")
        with path.open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
    else:
        raise EvidenceUnavailable("No configured owned evidence reader for this transport")
    if len(raw) > MAX_BYTES: raise EvidenceUnavailable("Artifact exceeds evidence limit")
    return raw, json.loads(raw)


def load(row, db):
    if db is None: return None
    compiled = row.submitted.get("compiled")
    if not isinstance(compiled, dict): return None
    metadata = compiled.get("solution_studio_metadata")
    if not isinstance(metadata, dict) or not isinstance(metadata.get("execution_instances"), list): return None
    instances = metadata["execution_instances"]
    if not instances: return None
    base = {"workflow_id": row.workflow_id, "submission_id": row.id, "source": "native Control task output",
            "limitations": "Algorithm evidence is checked separately from authenticated delivery receipts; neither establishes independent scientific qualification"}
    def unavailable(message):
        return {**base, "state": "unavailable", "message": message, "instances": []}
    deployment = db.query(Deployment).filter(Deployment.workflow_id == row.workflow_id).first()
    if (not deployment or row.phase != "submitted" or deployment.created_by_user_id != row.owner_user_id
            or deployment.solution_id != row.solution_id):
        return unavailable("Owned deployment and immutable submission association is unavailable")
    if row.submitted.get("runtime_destination") != settings.orchestrator_base_url:
        return unavailable("The recorded run belongs to a different runtime; no current service was queried")
    try:
        view(row)
        observed = get_workflow_tasks(row.workflow_id)
        if not isinstance(observed, dict) or observed.get("workflow_id") != row.workflow_id or not isinstance(observed.get("tasks"), list):
            return unavailable("Runtime task association differs from the recorded run")
        tasks = observed["tasks"]
        results = []
        for node in instances:
            identity = {key: node[key] for key in ("instance_id", "task_id", "node_key", "operation_name")}
            try:
                matching = [task for task in tasks if isinstance(task, dict) and task.get("task_id") == node["task_id"]]
                if len(matching) != 1 or matching[0].get("node_key") != node["node_key"]:
                    raise ValueError("Task identity differs from the submitted instance")
                task = matching[0]
                if task.get("status") not in {"completed", "complete"}:
                    results.append({**identity, "state": "pending", "message": "No completed algorithm output is recorded"}); continue
                outputs = task.get("output_refs", [])
                if (isinstance(outputs, list) and len(outputs) == 1 and isinstance(outputs[0], dict)
                        and outputs[0].get('protocol') in {'http', 'https'}):
                    from app.services.owned_control_result import inspect as inspect_control
                    try:
                        _, proof = inspect_control(row, node, task, db, tasks)
                        results.append(proof)
                    except HTTPException as exc:
                        results.append({**identity, 'state': 'unavailable', 'message': exc.detail})
                    continue
                if not isinstance(outputs, list) or len(outputs) != 1 or not isinstance(outputs[0], dict) or outputs[0].get("format") != "json":
                    results.append({**identity, "state": "unavailable", "message": "No single instrumented output is recorded"}); continue
                output_raw, output = read(outputs[0], row.workflow_id)
                renderer = output.get("input_consumption") if isinstance(output, dict) else None
                if not node.get("configuration") and renderer is None:
                    continue  # Preserve historical evidence without inventing consumption.
                proof = output.get("execution") if node.get("configuration") else renderer
                if not isinstance(proof, dict) or proof.get("schema_version") != "1.0":
                    results.append({**identity, "state": "unavailable", "message": "This operation has no supported consumption record"}); continue
                expected_identity = {"workflow_id": row.workflow_id, "task_id": node["task_id"], "operation_name": node["operation_name"]}
                if node.get("configuration"):
                    expected_identity["instance_id"] = node["instance_id"]
                    if (canonical(proof.get("configuration")) != canonical(node["configuration"])
                            or canonical(proof.get("algorithm_consumed")) != canonical(node["configuration"]["parameters"])
                            or proof.get("parameter_contract_sha256") != node["parameter_contract_sha256"]):
                        raise ValueError("Consumed values differ from the submitted instance")
                elif proof.get("kind") != "json-networks-render-v1":
                    raise ValueError("Unsupported input consumption contract")
                if any(proof.get(key) != value for key, value in expected_identity.items()):
                    raise ValueError("Observation identity differs from the submitted instance")
                expected = compiled.get("inputs", [])
                if node["input_bindings"]:
                    expected = []
                    for source_id in node["input_bindings"]:
                        source = next(n for n in instances if n["instance_id"] == source_id)
                        upstream = [t for t in tasks if isinstance(t, dict) and t.get("task_id") == source["task_id"] and t.get("node_key") == source["node_key"]]
                        if len(upstream) != 1: raise ValueError("Upstream task identity differs")
                        expected.extend(upstream[0].get("output_refs", []))
                inputs = task.get("input_refs", [])
                if len(inputs) != 1 or canonical(core(inputs)) != canonical(core(expected)):
                    raise ValueError("Observed input references differ from the recorded workflow")
                _, content = read(inputs[0], row.workflow_id)
                if hashlib.sha256(canonical(content)).hexdigest() != proof.get("input_sha256"):
                    raise ValueError("Algorithm input content differs from its recorded observation")
                if not node.get("configuration"):
                    networks = content.get("networks")
                    if (not isinstance(networks, list) or not networks
                            or type(proof.get("processed_network_count")) is not int
                            or proof["processed_network_count"] != len(networks)
                            or proof.get("networks_sha256") != hashlib.sha256(canonical(networks)).hexdigest()
                            or proof.get("processed_network_sha256") != [hashlib.sha256(canonical(n)).hexdigest() for n in networks]
                            or output.get("drawing_count") != len(networks) or output.get("topology_count") != len(networks)):
                        raise ValueError("Renderer processing differs from the actual input")
                output_hash = hashlib.sha256(output_raw).hexdigest()
                receipt_hash = hashlib.sha256(canonical({"output_sha256": output_hash, "input_sha256": proof["input_sha256"],
                                                        "configuration": node.get("configuration"), **identity})).hexdigest()
                receipt = db.get(InstanceEvidenceReceipt, (row.id, node["task_id"]))
                if receipt and receipt.manifest_sha256 != receipt_hash: raise ValueError("Previously inspected result changed")
                if receipt is None:
                    db.add(InstanceEvidenceReceipt(submission_id=row.id, task_id=node["task_id"], manifest_sha256=receipt_hash))
                    try: db.commit()
                    except IntegrityError:
                        db.rollback(); receipt = db.get(InstanceEvidenceReceipt, (row.id, node["task_id"]))
                        if receipt is None or receipt.manifest_sha256 != receipt_hash: raise ValueError("Concurrent result receipt differs")
                record = {**identity, "state": "available", "instrumentation": proof.get("instrumentation"),
                    "input_binding_verified": True, "input_sha256": proof["input_sha256"],
                    "output_sha256": output_hash, "manifest_sha256": receipt_hash,
                    "summary": {"topology_count": output.get("topology_count"), "drawing_count": output.get("drawing_count")}}
                if node.get("configuration"):
                    record.update(wrapper_received=proof["configuration"]["parameters"], algorithm_consumed=proof["algorithm_consumed"])
                else:
                    record["input_consumption"] = proof
                results.append(record)
            except (EvidenceUnavailable, OSError):
                results.append({**identity, "state": "inaccessible", "message": "Instrumented output or input is unavailable in the authorized artifact volume"})
            except (ValueError, KeyError, TypeError, StopIteration):
                results.append({**identity, "state": "conflicting", "message": "Algorithm output failed identity, input or integrity validation"})
        return {**base, "state": "available" if results and all(item["state"] == "available" for item in results) else "unavailable", "instances": results}
    except (HTTPException, ValueError, KeyError, TypeError):
        return unavailable("Recorded runtime observations are unavailable; submitted settings remain unchanged")
