"""Automatic capture integration, enabled only in the isolated Dutch pilot.

Submission inputs are committed before calling the orchestrator. Collection
accepts only immutable manifests carrying that exact workflow/task/request and
upstream digest. Existing historical registrations are never modified.
"""
import base64
import json
from pathlib import Path
from uuid import uuid4
from sqlalchemy.engine import make_url

from fastapi import HTTPException

from app.core.config import settings
from app.models.deployment import Deployment
from app.models.local_dutch_execution import LocalDutchExecution
from app.models.service import Service
from app.services import local_dutch_evidence as historical
from app.services.dutch_capture_contract import (BASE_IMAGES, VERSION, SOURCE_REVISION, NODE_KEYS, NAMES,
    confined_read, encode, output_ref, sha, task_id, validate_ids)

EVIDENCE_SOURCE = "Validated immutable captures recorded for this run"

LABELS = {"configuration": "Configuration (JSON)", "grid": "Grid data (JSON)",
          "network": "Graph (pandapower JSON)", "benchmark": "Benchmark results (JSON safe export)"}


def enabled():
    from app.services.qualified_demo import profile_enabled
    return bool((historical.enabled() or qualification_enabled() or profile_enabled())
                and settings.local_dutch_auto_capture_root and settings.local_dutch_capture_runtime)


def qualification_enabled():
    url = make_url(settings.database_url)
    return (settings.aie37_qualification and url.host == "postgres"
            and url.database == "design_aie37_qualification"
            and settings.orchestrator_base_url == "http://seed-orchestrator:8000"
            and not settings.design_ai_enabled and not settings.openai_api_key)


def runtime_identity():
    path = Path(settings.local_dutch_capture_runtime)
    value = json.loads(confined_read(path.parent, path.name))
    if value["version"] != VERSION or value["source_revision"] != SOURCE_REVISION:
        raise ValueError("Wrong capture runtime")
    for role in BASE_IMAGES:
        if value["images"][role]["base_image"] != BASE_IMAGES[role]:
            raise ValueError("Wrong baseline lineage")
    return value


def prepare_submission(db, user, workflow, compiled):
    from app.services.qualified_demo import profile_enabled
    if not enabled():
        return None
    endpoints = compiled["dockerinfo"]["docker_info_list"]
    nodes = compiled["blueprint"]["nodes"]
    keys = [n["container_name"] + ":" + n["operation_signature_list"][0]["operation_signature"]["operation_name"] for n in nodes]
    if set(keys) != set(NODE_KEYS.values()) or len(nodes) != 2:
        if qualification_enabled() or profile_enabled():
            raise HTTPException(422, "This qualification permits only the reviewed Dutch generation-to-benchmark chain")
        return None
    by_key = dict(zip(keys, nodes))
    links = by_key[NODE_KEYS["synth"]]["operation_signature_list"][0].get("connected_to", [])
    downstream = by_key[NODE_KEYS["benchmark"]]["operation_signature_list"][0].get("connected_to", [])
    expected_link = [{"container_name": "benchmark-runner", "operation_signature": {"operation_name": "RunBenchmark"}}]
    if links != expected_link or downstream:
        raise HTTPException(422, "Automatic capture supports only the existing synthesis-to-benchmark chain")
    if not workflow.solution_id:
        raise HTTPException(422, "Automatic local capture requires an owned saved solution")
    if {(e["container_name"], e["ip_address"], str(e["port"])) for e in endpoints} != {
            ("grid_synth_service", "seed-synth", "8080"), ("benchmark-runner", "seed-benchmark", "8080")}:
        raise HTTPException(409, "This capture supports only the isolated Dutch runtime")
    value = workflow.run_input
    if qualification_enabled() or profile_enabled():
        if (value is not None or compiled["solution_studio_metadata"]["capability_bindings"]["status"] != "verified"
                or not compiled.get("task_configurations")):
            raise HTTPException(422, "Qualification requires explicit connections and saved instance settings, without workflow seed input")
    if value is not None and (set(value) != {"seed"} or type(value["seed"]) is not int or value["seed"] not in (42, 43)):
        raise HTTPException(422, "Local Dutch capture supports only recorded integer seed 42 or 43")
    refs = compiled.get("inputs", [])
    try:
        if value is None:
            if refs != []:
                raise ValueError("Unexpected compiled input")
        else:
            if len(refs) != 1 or refs[0]["protocol"] != "inline" or refs[0]["format"] != "json":
                raise ValueError("Unsupported compiled input")
            if json.loads(base64.b64decode(refs[0]["uri"], validate=True)) != value:
                raise ValueError("Compiled seed mismatch")
    except (ValueError, KeyError, TypeError):
        raise HTTPException(422, "Compiled input does not match the saved submission snapshot")
    try:
        pins = runtime_identity()
    except (OSError, ValueError, KeyError, TypeError):
        raise HTTPException(503, "Local capture runtime identity is unavailable; no workflow was submitted")
    snapshot = {"request": workflow.model_dump(mode="json"), "root_refs": compiled.get("inputs", []),
                "blueprint": compiled["blueprint"], "dockerinfo": compiled["dockerinfo"], "runtime": pins}
    if qualification_enabled() or profile_enabled():
        snapshot["task_configurations"] = compiled["task_configurations"]
        snapshot["capability_bindings"] = compiled["solution_studio_metadata"]["capability_bindings"]
    record = LocalDutchExecution(id=str(uuid4()), solution_id=workflow.solution_id, owner_user_id=user.id,
                                 submitted=json.loads(encode(snapshot)), phase="prepared")
    if qualification_enabled():
        # A failed submission still consumes this one-time execution permission.
        # Lock the shared source row so concurrent solutions cannot race the cap.
        guard = db.query(Service).filter(Service.id == "aie37-synth").with_for_update().first()
        if guard is None or db.query(LocalDutchExecution).count():
            raise HTTPException(409, "The one AIE-37 local execution permission has been consumed. Preserve its outcome; no resubmission is authorized.")
    db.add(record)
    db.commit()  # Must be durable before any execution request leaves Studio.
    return record


def attach_workflow(db, snapshot, result, user):
    if snapshot is None:
        return
    workflow = result.get("workflow_id", "")
    validate_ids(workflow, task_id("synth"))
    snapshot.workflow_id, snapshot.phase = workflow, "submitted"
    existing = db.query(Deployment).filter(Deployment.workflow_id == workflow).first()
    if existing is None:
        db.add(Deployment(id=str(uuid4()), workflow_id=workflow, solution_id=snapshot.solution_id,
                          created_by_user_id=user.id, name=snapshot.submitted["request"]["name"], status=result.get("status", "submitted")))
    elif existing.created_by_user_id != user.id or existing.solution_id != snapshot.solution_id:
        raise HTTPException(409, "Recorded execution ownership differs from capture")
    db.commit()


def _refs(refs):
    return [{k: r[k] for k in ("protocol", "format", "uri")} for r in refs]


def _read_role(root, workflow, role, snapshot):
    task = task_id(role)
    prefix = f"{role}/{workflow}/{task}/"
    manifest_bytes = confined_read(root, prefix + "manifest.json")
    manifest = json.loads(manifest_bytes)
    request_bytes = confined_read(root, prefix + "request.json", manifest["request_sha256"])
    request = json.loads(request_bytes)
    expected = snapshot["runtime"]
    provenance = manifest["provenance"]
    if ((manifest["version"], manifest["workflow_id"], manifest["task_id"], manifest["role"], manifest["status"])
            != (VERSION, workflow, task, role, "complete")
            or (request["workflow_id"], request["task_id"], request["method"])
            != (workflow, task, NODE_KEYS[role].split(":")[1])
            or manifest["method"] != request["method"]
            or provenance != {"version": VERSION, "base_image": BASE_IMAGES[role], "source_revision": SOURCE_REVISION,
                              "adapter_sha256": expected["adapter_sha256"], "contract_sha256": expected["contract_sha256"]}):
        raise ValueError("Execution or runtime association mismatch")
    if role == "synth" and _refs(request["inputs"]) != _refs(snapshot["root_refs"]):
        raise ValueError("Submitted input mismatch")
    if "task_configurations" in snapshot:
        expected_configuration = snapshot["task_configurations"].get(NODE_KEYS[role])
        if request.get("configuration") != expected_configuration:
            raise ValueError("Submitted instance settings mismatch")
    keys = ("configuration", "grid", "network") if role == "synth" else ("benchmark", "benchmark_source")
    blobs = {key: confined_read(root, prefix + NAMES[key], manifest["files"][key]["sha256"]) for key in keys}
    return manifest, manifest_bytes, request, blobs


def recorded_state(db, deployment):
    """Only this new attempt's terminal observation may replace an unavailable live read."""
    if not enabled():
        return None
    record = db.query(LocalDutchExecution).filter(LocalDutchExecution.workflow_id == deployment.workflow_id).first()
    if (not record or not record.submitted.get("request", {}).get("submission_id")
        or record.owner_user_id != deployment.created_by_user_id or record.solution_id != deployment.solution_id):
        return None
    collection = record.collection or {}
    observation = collection.get("terminal_observation")
    if (not isinstance(observation, dict) or sha(encode(observation)) != collection.get("terminal_observation_sha256")
        or observation.get("workflow", {}).get("workflow_id") != deployment.workflow_id
        or observation["workflow"].get("status") not in {"completed", "failed"}):
        return None
    tasks = observation.get("tasks")
    if (not isinstance(tasks, list) or len(tasks) != 2
        or any(not isinstance(task, dict) for task in tasks)
        or {(task.get("task_id"), task.get("node_key")) for task in tasks}
            != {(task_id(role), key) for role, key in NODE_KEYS.items()}
        or any(task.get("workflow_id", deployment.workflow_id) != deployment.workflow_id for task in tasks)):
        return None
    return observation["workflow"], tasks


def associated_state(db, deployment, read_live=None):
    """Prefer this run's recorded terminal observation; always revalidate files."""
    recorded = recorded_state(db, deployment)
    if recorded:
        return *recorded, False, "recorded terminal observation for this run"
    if read_live is None:
        from app.services.orchestrator_adapter import get_workflow_status, get_workflow_tasks
        def read_live(value):
            try:
                return get_workflow_status(value.workflow_id), get_workflow_tasks(value.workflow_id)["tasks"], True
            except (HTTPException, KeyError):
                return {"workflow_id": value.workflow_id, "status": value.status}, [], False
    workflow, tasks, live = read_live(deployment)
    return workflow, tasks, live, "orchestrator" if live else "stored deployment record; task observation unavailable"


def collect(db, deployment, workflow, tasks, *, runtime_live=True):
    if not enabled():
        return None
    record = (db.query(LocalDutchExecution).filter(LocalDutchExecution.workflow_id == deployment.workflow_id)
              .execution_options(populate_existing=True).with_for_update().first())
    if record is None:
        return None
    if record.owner_user_id != deployment.created_by_user_id or record.solution_id != deployment.solution_id:
        return {"state": "inaccessible", "message": "Execution association rejected.", "execution_input": None, "artifacts": []}, {}
    snapshot, wid = record.submitted, deployment.workflow_id
    result = {"state": "pending", "message": "Results collection pending.",
              "execution_input": snapshot["request"]["run_input"], "input_source": "Saved submission snapshot recorded before execution",
              "grid": None, "benchmark": None, "artifacts": [], "roles": {}, "source": EVIDENCE_SOURCE, "historical": workflow.get("status") in {"completed", "failed"},
              "source_revision": SOURCE_REVISION, "capture_version": VERSION,
              "adapter_sha256": snapshot["runtime"]["adapter_sha256"],
              "images": {k: v["id"] for k, v in snapshot["runtime"]["images"].items()},
              "limitations": "Local derived capture runtime; baseline images preserved. KPI units were not recorded. Temporary benchmark CSVs are not retained. Production compatibility unverified."}
    blobs, manifests, accepted = {}, {}, dict((record.collection or {}).get("manifests", {}))
    failures, waiting, stopped = [], [], []
    for role in BASE_IMAGES:
        role_keys = ("configuration", "grid", "network") if role == "synth" else ("benchmark",)
        identity = {"workflow_id": wid, "task_id": task_id(role), "node_key": NODE_KEYS[role]}
        matches = [t for t in tasks if t.get("task_id") == task_id(role) and t.get("node_key") == NODE_KEYS[role]]
        conflicting = (workflow.get("workflow_id") != wid or len(matches) > 1
            or any(t.get("workflow_id", wid) != wid for t in matches)
            or any((t.get("task_id") == task_id(role) or t.get("node_key") == NODE_KEYS[role]) and t not in matches for t in tasks))
        task = matches[0] if len(matches) == 1 else None
        if conflicting:
            failures.append(role)
            result["roles"][role] = {**identity, "state": "conflicting", "message": "Workflow or task observation does not match this recorded operation."}
            result["artifacts"].extend({"id": key, "label": LABELS[key], "state": "inaccessible", "task_id": task_id(role)} for key in role_keys)
            continue
        if task is None or task.get("status") != "completed":
            finished_with_failure = workflow.get("status") == "failed" or (task and task.get("status") == "failed")
            (stopped if finished_with_failure else waiting).append(role)
            result["roles"][role] = {**identity,
                "state": "unavailable" if finished_with_failure or task is None else "pending",
                "message": "This task failed; completed consumption evidence was not recorded." if finished_with_failure else
                    "No matching task observation is available for this run." if task is None else "This task has not completed."}
            for key in role_keys:
                result["artifacts"].append({"id": key, "label": LABELS[key],
                    "state": "not_recorded" if finished_with_failure else "pending", "task_id": task_id(role)})
            continue
        try:
            manifest, data, request, files = _read_role(settings.local_dutch_auto_capture_root, wid, role, snapshot)
            if "capability_bindings" in snapshot:
                if (_refs(task.get("input_refs", [])) != _refs(request["inputs"])
                        or _refs(task.get("output_refs", [])) != [output_ref(wid, task_id(role), data)]):
                    raise ValueError("Orchestrator references do not match the captured execution")
            digest = sha(data)
            if role in accepted and accepted[role] != digest:
                raise ValueError("Previously accepted execution evidence changed")
            if role == "synth":
                grid = json.loads(files["grid"])["grid_data"]
                config = json.loads(files["configuration"])["config"]
                supplied = snapshot["request"]["run_input"]
                configuration = snapshot.get("task_configurations", {}).get(NODE_KEYS["synth"])
                actual_seed = configuration["parameters"]["seed"] if configuration else supplied["seed"] if supplied is not None else 42
                if configuration:
                    recorded = json.loads(files["configuration"])
                    if recorded.get("algorithm_consumed") != configuration["parameters"]:
                        raise ValueError("Algorithm consumption was not recorded")
                if grid["seed"] != config["seed"] or grid["source_config"]["seed"] != config["seed"] or config["seed"] != actual_seed:
                    raise ValueError("Seed evidence mismatch")
                if files["network"] != grid["pandapower_json"].encode():
                    raise ValueError("Graph evidence mismatch")
                if configuration:
                    result["algorithm_consumed"] = recorded["algorithm_consumed"]
                    result["input_source"] = "Saved instance settings; verified at the grid generation algorithm"
                result["executed_seed"] = config["seed"]
                result["grid"] = {"grid_id": grid["grid_id"], "seed": grid["seed"],
                                  "nodes": int(grid["metadata"]["nodes"]), "edges": int(grid["metadata"]["edges"])}
            else:
                if "synth" not in manifests:
                    raise ValueError("Upstream execution not validated")
                synth_manifest, synth_bytes, _ = manifests["synth"]
                expected_ref = output_ref(wid, task_id("synth"), synth_bytes)
                if _refs(request["inputs"]) != [expected_ref]:
                    raise ValueError("Benchmark consumed another execution")
                upstream = {"workflow_id": wid, "task_id": task_id("synth"), "manifest_sha256": sha(synth_bytes),
                            "grid_sha256": synth_manifest["files"]["grid"]["sha256"]}
                if manifest["upstream"] != upstream:
                    raise ValueError("Upstream capture association mismatch")
                bench = json.loads(files["benchmark"])
                if bench["source_sha256"] != sha(files["benchmark_source"]) or any(bench["upstream"].get(k) != v for k, v in upstream.items()):
                    raise ValueError("Benchmark output association mismatch")
                if (bench["upstream"]["grid_id"], bench["upstream"]["nodes"], bench["upstream"]["edges"]) != (result["grid"]["grid_id"], result["grid"]["nodes"], result["grid"]["edges"]):
                    raise ValueError("Grid/benchmark mismatch")
                result["benchmark"] = bench
                if "capability_bindings" in snapshot:
                    result["verified_bindings"] = snapshot["capability_bindings"]["bindings"]
            manifests[role] = (manifest, data, request)
            accepted[role] = digest
            result["roles"][role] = {**identity, "state": "available", "historical": True,
                "source": EVIDENCE_SOURCE,
                "message": "Recorded algorithm parameters match the submitted configuration." if role == "synth" else
                    "Recorded benchmark input matches this run's validated upstream grid.",
                "algorithm_consumed": result.get("algorithm_consumed") if role == "synth" else None,
                "input_binding_verified": role == "benchmark" and bool(result.get("verified_bindings")),
                "output_sha256": sha(files["grid" if role == "synth" else "benchmark"])}
            for key in role_keys:
                blobs[key] = files[key]
                result["artifacts"].append({"id": key, "label": LABELS[key], "state": "available", "task_id": task_id(role),
                    "sha256": sha(files[key]), "size_bytes": len(files[key]),
                    "download_url": f"/api/deployments/by-workflow/{wid}/artifacts/{key}"})
        except FileNotFoundError:
            result["roles"][role] = {**identity, "state": "inaccessible", "message": "A completed capture file is not yet available; no evidence was inferred from task completion."}
            failed_path = f"{role}/{wid}/{task_id(role)}/failed.json"
            try:
                failed = json.loads(confined_read(settings.local_dutch_auto_capture_root, failed_path))
                if failed.get("state") == "failed":
                    failures.append(role)
                else:
                    waiting.append(role)
            except (OSError, ValueError):
                waiting.append(role)
            for key in role_keys:
                result["artifacts"].append({"id": key, "label": LABELS[key], "state": "inaccessible", "task_id": task_id(role)})
        except (OSError, ValueError, KeyError, TypeError) as exc:
            conflict = str(exc) in {"Execution or runtime association mismatch", "Submitted input mismatch",
                "Submitted instance settings mismatch", "Orchestrator references do not match the captured execution",
                "Previously accepted execution evidence changed", "Benchmark consumed another execution",
                "Upstream capture association mismatch", "Benchmark output association mismatch", "Grid/benchmark mismatch"}
            result["roles"][role] = {**identity,
                "state": "inaccessible" if isinstance(exc, OSError) else "conflicting" if conflict else "invalid",
                "message": "Capture files could not be read." if isinstance(exc, OSError) else
                    "Capture association conflicts with this run or its previously accepted evidence." if conflict else
                    "Capture integrity or recorded algorithm evidence failed validation."}
            failures.append(role)
            for key in role_keys:
                result["artifacts"].append({"id": key, "label": LABELS[key], "state": "inaccessible", "task_id": task_id(role)})
    if failures:
        result.update(state="collection_failed", message="Execution status is shown separately. Some results failed association or integrity checks.")
    elif stopped:
        result.update(state="unavailable", message="Some tasks failed; no completed output was recorded for those tasks.")
    elif waiting:
        terminal = workflow.get("status") in ("completed", "failed")
        result.update(state="delayed" if terminal else "pending",
                      message="Execution finished; some recorded outputs are not yet available." if terminal else "Results pending while tasks run.")
    else:
        result.update(state="available", message="Results captured automatically for this execution.")
    collection = {"state": result["state"], "manifests": accepted}
    previous = record.collection or {}
    for key in ("terminal_observation", "terminal_observation_sha256"):
        if key in previous:
            collection[key] = previous[key]
    complete_task_identity = (len(tasks) == 2 and workflow.get("workflow_id") == wid
        and all(task.get("workflow_id", wid) == wid for task in tasks)
        and {(task.get("task_id"), task.get("node_key")) for task in tasks} == {(task_id(role), key) for role, key in NODE_KEYS.items()})
    if (snapshot["request"].get("submission_id") and runtime_live and complete_task_identity and workflow.get("status") in {"completed", "failed"}
        and "terminal_observation" not in collection):
        observation = {"workflow": {"workflow_id": wid, "status": workflow["status"]},
            "tasks": [{key: value for key, value in task.items() if key in {"task_id", "node_key", "status", "input_refs", "output_refs"}}
                for task in tasks]}
        collection.update(terminal_observation=observation, terminal_observation_sha256=sha(encode(observation)))
        deployment.status = workflow["status"]
    if record.collection != collection:
        record.collection = collection
        db.commit()
    return result, blobs
