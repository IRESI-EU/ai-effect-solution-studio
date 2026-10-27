"""No SDK/network: only the isolated profile's explicit dispatch block."""
import json
from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "deploy/instance-edit"))
from verification_guard import install_guard, PROMPTS


@pytest.fixture
def guarded(tmp_path):
    app = FastAPI()
    calls = []
    @app.post("/{path:path}")
    def reached(path: str):
        calls.append(path)
        return {"ok": True}
    install_guard(app, tmp_path, {"A": {"draft_id": "a"}, "B": {"draft_id": "b"}})
    return TestClient(app), tmp_path, calls


@pytest.mark.parametrize("path", ["/workflows/submit", "/workflows/compile", "/workflows/runtime-preflight", "/deployments", "/services/x/verify-runtime", "/design-ai/drafts/b/apply", "/design-ai/drafts/b/save"])
def test_submission_and_unapproved_mutation_never_reach_application(guarded, path):
    client, directory, calls = guarded
    assert client.post(path, json={}).status_code == 403
    assert calls == []


def test_exact_cases_once_persistent_across_clients_and_no_unscoped_chat(guarded):
    client, directory, calls = guarded
    request = {"draft_id": "a", "revision": 0, "history": [], "message": PROMPTS["A"]}
    assert client.post("/design-ai/chat", json=request).status_code == 403
    (directory / "live-preflight.json").write_text("{}")
    assert client.post("/design-ai/chat", json={**request, "message": "something else"}).status_code == 403
    assert client.post("/design-ai/chat", json=request).status_code == 200
    assert client.post("/design-ai/chat", json=request).status_code == 409
    assert client.post("/design-ai/chat", json={**request, "draft_id": "b", "message": PROMPTS["B"]}).status_code == 200
    assert calls == ["design-ai/chat", "design-ai/chat"]
    assert json.loads((directory / "chat-A-result.json").read_text()) == {"ok": True}
