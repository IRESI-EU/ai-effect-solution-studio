"""Read-only verification of the one explicitly identified qualification run.

Never creates a design, submits, retries, repairs an artifact or calls a provider.
Use a new output filename to preserve each verification checkpoint.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import requests

def sha(data):
    return hashlib.sha256(data).hexdigest()
def verify(private, output):
    record = json.loads((private / "prepared.json").read_text(encoding="utf-8"))
    wid, sid = record["workflow_id"], record["solution_id"]
    assert wid and record["submission_attempted"] and record["execution_limit"] == 1
    session = requests.Session()
    session.trust_env = False
    api, web = "http://127.0.0.1:28185", "http://127.0.0.1:23121"
    login = session.post(api + "/auth/login", json=json.loads((private / "reviewer.json").read_text()), timeout=20)
    assert login.status_code == 200 and login.json()["id"] == "aie37-designer"
    result = session.get(api + f"/deployments/by-workflow/{wid}/results", timeout=30)
    assert result.status_code == 200
    value = result.json()
    assert value["deployment"]["solution_id"] == sid and value["deployment"]["created_by_user_id"] == "aie37-designer"
    assert value["workflow"]["status"] == "completed", "Preserve any failure; never resubmit"
    evidence = value["evidence"]
    assert evidence["state"] == "available" and evidence["algorithm_consumed"] == {"seed": 43}
    assert evidence["grid"]["seed"] == 43 and evidence["verified_bindings"] == record["pre_submission"]["compiled"]["solution_studio_metadata"]["capability_bindings"]["bindings"]
    tasks = {t["node_key"]: t for t in value["tasks"]}
    source, consumer = tasks["grid_synth_service:ConfigureAndSynthesize"], tasks["benchmark-runner:RunBenchmark"]
    def core(refs):
        return [{k: r[k] for k in ("protocol", "uri", "format")} for r in refs]
    assert core(source["output_refs"]) == core(consumer["input_refs"])
    assert source["status"] == consumer["status"] == "completed"
    snapshot = session.get(api + f"/workflows/{wid}/submitted-configuration", timeout=20)
    assert snapshot.status_code == 200
    snap = snapshot.json()
    assert snap["submitted"]["compiled"]["task_configurations"]["grid_synth_service:ConfigureAndSynthesize"]["parameters"] == {"seed": 43}
    downloaded = {}
    for artifact in evidence["artifacts"]:
        response = session.get(web + artifact["download_url"], timeout=30)
        assert response.status_code == 200 and sha(response.content) == artifact["sha256"]
        assert response.headers["cache-control"] == "private, no-store"
        assert response.headers["x-content-type-options"] == "nosniff"
        role = "benchmark" if artifact["id"] == "benchmark" else "synth"
        filename = {"configuration": "configuration.json", "grid": "grid.json", "network": "network.pandapower.json", "benchmark": "benchmark.json"}[artifact["id"]]
        code = "import hashlib; from pathlib import Path; print(hashlib.sha256(Path(" + repr("/run-evidence/" + wid + "/" + artifact["task_id"] + "/" + filename) + ").read_bytes()).hexdigest())"
        actual = subprocess.check_output(["docker", "exec", "ai-effect-aie37-seed-" + role + "-1", "python", "-c", code], text=True).strip()
        assert actual == artifact["sha256"]
        anonymous = requests.get(web + artifact["download_url"], timeout=20)
        assert anonymous.status_code == 401
        downloaded[artifact["id"]] = {"sha256": actual, "bytes": len(response.content), "proxy_download": 200, "anonymous": 401}
    current = session.get(api + "/solutions/" + sid, timeout=20).json()
    seed = next(n["data"]["configuration"]["parameters"]["seed"] for n in current["nodes"] if n["id"] == "generate-grid")
    result = {"workflow_id": wid, "solution_id": sid, "results": value, "submission": snap,
              "downloads": downloaded, "current_draft_seed": seed, "new_execution_requests": 0}
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps({"workflow_id": wid, "status": "completed", "evidence": "available", "recorded_seed": 43,
                      "current_draft_seed": seed, "matching_downloads": len(downloaded), "anonymous_downloads": "401",
                      "downstream_reference_matches": True, "workflow_requests_made": 0}))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    verify(args.private_dir.resolve(), args.output.resolve())
