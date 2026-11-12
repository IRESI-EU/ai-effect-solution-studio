"""Recheck the completed local proof without editing designs or executing.

Only normal existing-account login and authorized GET routes are used. No
provider, grant, submission, readiness or retry route exists in this helper.
"""
import argparse
import hashlib
import json
from pathlib import Path
import requests

WEB = "http://127.0.0.1:23121"
RUNS = {42: "wf-3cc4e38fc14a", 43: "wf-386fded9b8bb"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-checkout", type=Path, required=True)
    args = parser.parse_args()
    credentials = args.original_checkout / "local-backups/aie37-profile-20261028/reviewer.json"
    session, anonymous = requests.Session(), requests.Session()
    session.trust_env = anonymous.trust_env = False
    login = session.post(WEB + "/api/auth/login", json=json.loads(credentials.read_text()), timeout=20)
    if login.status_code != 200:
        raise RuntimeError("Existing local sign-in failed; credentials were not printed or changed")
    result = {}
    for seed, workflow in RUNS.items():
        response = session.get(WEB + "/api/deployments/by-workflow/" + workflow + "/results", timeout=20)
        response.raise_for_status()
        run = response.json()
        evidence = run["evidence"]
        assert run["workflow"]["status"] == "completed" and evidence["state"] == "available"
        assert len(run["tasks"]) == 2 and all(t["status"] == "completed" for t in run["tasks"])
        assert evidence["algorithm_consumed"] == {"seed": seed}
        artifacts = {a["id"]: a for a in evidence["artifacts"]}
        assert len(artifacts) == 4
        for name, artifact in artifacts.items():
            assert artifact["download_url"].startswith("/api/deployments/by-workflow/" + workflow + "/artifacts/")
            downloaded = session.get(WEB + artifact["download_url"], timeout=20)
            assert downloaded.status_code == 200
            assert hashlib.sha256(downloaded.content).hexdigest() == artifact["sha256"]
            assert anonymous.get(WEB + artifact["download_url"], timeout=10).status_code == 401
            if name == "configuration":
                assert downloaded.json()["algorithm_consumed_steps"] == {
                    "InputConfigurator.create_params": {"seed": seed},
                    "PowerGridGenerator.generate_grid": {"seed": seed}}
        assert evidence["benchmark"]["upstream"]["workflow_id"] == workflow
        assert evidence["benchmark"]["upstream"]["grid_sha256"] == artifacts["grid"]["sha256"]
        result[str(seed)] = {"workflow": workflow, "status": "passed",
                            "verified_downloads": 4, "new_executions": 0}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
