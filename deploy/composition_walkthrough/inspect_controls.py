"""Read-only design snapshots and bounded rejection checks for agent evidence.

Only the disposable loopback harness. Never Apply/Undo/Save a valid action here;
the browser performs those actions. Human recommendation is never created.
"""
import argparse
import json
from pathlib import Path
import httpx

BASE = "http://127.0.0.1:28187"


def inspect(profile, stage, verify=False):
    credentials = json.loads((profile / "private-credentials.json").read_text())
    with httpx.Client(base_url=BASE, timeout=10, trust_env=False) as client:
        assert client.post("/auth/login", json=credentials["agent"]).status_code == 200
        drafts = client.get("/design-ai/drafts").json()
        assert len(drafts) == 1
        base = "/design-ai/drafts/" + drafts[0]["id"]
        response = client.get(base); assert response.status_code == 200
        value = response.json()
        (profile.parent / (stage + ".json")).write_text(json.dumps(value, indent=2), encoding="utf-8")
        if verify:
            assert value["revision"] == 3 and value["saved_solution_id"] and not value["pending"]
            assert value["design"] == json.loads((profile.parent / "agent-r1.json").read_text())["design"]
            undone = json.loads((profile.parent / "agent-r2.json").read_text())
            assert undone["design"]["nodes"] == undone["design"]["edges"] == []
            assert undone["pending"]["design"] == value["design"]
            solution = client.get("/solutions/" + value["saved_solution_id"]).json()
            assert solution["nodes"] == value["design"]["nodes"] and solution["edges"] == value["design"]["edges"]
            assert solution["design_metadata"]["source"]["kind"] == "catalogue_composed"
            assert solution["design_metadata"]["execution_policy"] == "design_only_catalogue_pair"
            assert "template_key" not in value and value["source"]["kind"] == "catalogue_composed"
            results = {}
            for action, body in (("apply", {"revision": 0, "proposal_id": undone["pending"]["id"]}), ("undo", {"revision": 1}), ("save", {"revision": 2})):
                code = client.post(base + "/" + action, json=body).status_code
                assert code == 409, (action, code)
                results["stale_" + action] = code
            for path in ("/workflows/runtime-preflight", "/workflows/submit-to-orchestrator", base + "/execution-review", "/design-ai/chat"):
                code = client.post(path, json={}).status_code
                assert code == 403, (path, code)
                results[path] = code
            assert client.get(base).json()["design"] == value["design"]
            assert client.post("/auth/logout").status_code == 204
            assert client.post("/auth/login", json=credentials["human"]).status_code == 200
            assert client.get("/design-ai/drafts").json() == []
            for suffix, body in (("", None), ("/apply", {"revision":3,"proposal_id":"not-authorized"}), ("/save", {"revision":3})):
                response = client.get(base) if body is None else client.post(base + suffix, json=body)
                assert response.status_code == 404
                results["other_owner" + suffix] = response.status_code
            assert client.get("/design-ai/drafts").json() == []
            (profile.parent / "focused-protections.json").write_text(json.dumps(results, indent=2))
        print(json.dumps({"stage":stage,"draft":value["id"],"revision":value["revision"],"node_count":len(value["design"]["nodes"]),"saved_solution":value["saved_solution_id"],"verified_protections":verify}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--stage", required=True, choices=("agent-r1", "agent-r2", "agent-saved"))
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    inspect(args.profile.resolve(strict=True), args.stage, args.verify)
