"""Real authorized route, isolated SQLite and explicit server task observations."""
import base64
import hashlib
import json

import pytest

from app.models.deployment import Deployment
from app.models.execution_submission import ExecutionSubmission
from app.services import owned_artifact_preview as owned


@pytest.fixture
def observed(environment, db, monkeypatch, tmp_path):
    for workflow, owner in (("wf-owned", "designer"), ("wf-other", "other"), ("wf-legacy", None)):
        db.add(Deployment(id=workflow, workflow_id=workflow, name=workflow, status="completed", created_by_user_id=owner))
    db.commit()
    value = {"request":{},"compiled":{}}
    db.add(ExecutionSubmission(id="submitted-owned",workflow_id="wf-owned",owner_user_id="designer",
        solution_id=None,phase="submitted",submitted=value,
        submitted_sha256=hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()))
    db.commit()
    monkeypatch.setenv("ARTIFACT_BASE_PATH", str(tmp_path))
    monkeypatch.setenv("ARTIFACT_BASE_PATHS", "")
    directory = tmp_path / "wf-owned"
    directory.mkdir()
    artifact = directory / "result.json"
    artifact.write_text('{"answer":43}')
    calls = []
    state = {"workflow_id":"wf-owned","tasks":[{"task_id":"task_owned","result":{"output":{"protocol":"file","uri":"/data/wf-owned/result.json"}}}]}
    def tasks(workflow):
        calls.append(workflow)
        return state
    monkeypatch.setattr(owned, "get_workflow_tasks", tasks)
    return state, calls, artifact


def request(environment, **changes):
    return environment.post("/data-references/preview", json={"workflow_id":"wf-owned","task_id":"task_owned", "protocol":"file","uri":"/data/wf-owned/result.json", **changes})


def test_owned_task_output_previews_but_omitted_authority_cannot(environment, observed):
    result = request(environment)
    assert result.status_code == 200
    assert result.json()["content"] == {"answer":43}
    assert environment.post("/data-references/preview",json={"protocol":"file","uri":"/data/wf-owned/result.json"}).status_code == 422


def test_other_owner_denied_before_runtime_or_storage_read(environment, observed, monkeypatch):
    state, calls, _ = observed
    monkeypatch.setattr(owned,"resolve_artifact_path",lambda _: pytest.fail("must authorize first"))
    assert request(environment, workflow_id="wf-other").status_code == 403
    assert calls == []


def test_wrong_workflow_task_or_reference_never_reads_content(environment, observed, monkeypatch):
    state, _, _ = observed
    monkeypatch.setattr(owned,"preview_data_reference",lambda *args: pytest.fail("must validate association first"))
    assert request(environment, task_id="task_other").status_code == 404
    state["workflow_id"] = "wf-other"
    assert request(environment).status_code == 409
    state["workflow_id"] = "wf-owned"
    state["tasks"][0]["result"] = None
    assert request(environment).status_code == 403


def test_inputs_do_not_confer_output_authority(environment, observed):
    state, _, _ = observed
    state["tasks"][0]["input"] = state["tasks"][0].pop("result")
    assert request(environment).status_code == 403


def test_shared_or_cross_workflow_file_is_not_assigned_to_caller(environment, observed, tmp_path):
    state, _, _ = observed
    path = tmp_path / "wf-other"
    path.mkdir()
    (path / "result.json").write_text('{"private":true}')
    uri = "/data/wf-other/result.json"
    state["tasks"][0]["result"]["output"]["uri"] = uri
    assert request(environment, uri=uri).status_code == 409
    assert request(environment, uri="/data/wf-owned/../wf-other/result.json").status_code == 409


def test_remote_uris_never_trigger_remote_fetch(environment, observed, monkeypatch):
    state, _, _ = observed
    state["tasks"][0]["result"] = {"protocol":"http","uri":"http://private.example/secret"}
    monkeypatch.setattr(owned,"preview_data_reference",lambda *args: pytest.fail("remote fetch forbidden"))
    assert request(environment, protocol="http",uri="http://private.example/secret").status_code == 409


def test_inline_requires_exact_observed_output(environment, observed):
    state, _, _ = observed
    uri = base64.b64encode(b'{"value":43}').decode()
    state["tasks"][0]["result"] = {"protocol":"inline","uri":uri}
    assert request(environment,protocol="inline",uri=uri).json()["content"] == {"value":43}
    assert request(environment,protocol="inline",uri=uri + "wrong").status_code == 403


def test_unknown_legacy_owner_stays_unassigned_even_for_admin(environment, observed, db):
    from app.models.user import User
    user = db.get(User,"designer"); user.role="platform_admin"; db.commit()
    assert request(environment, workflow_id="wf-legacy").status_code == 409
    assert observed[1] == []


def test_runtime_outage_is_unavailable_not_a_cached_authorization(environment, observed, monkeypatch):
    from fastapi import HTTPException
    def unavailable(_): raise HTTPException(503,"Task observations unavailable")
    monkeypatch.setattr(owned,"get_workflow_tasks",unavailable)
    assert request(environment).status_code == 503


def test_directory_children_stay_within_resolved_owned_output(environment, observed):
    state, _, artifact = observed
    state["tasks"][0]["result"] = {"protocol":"file","uri":"/data/wf-owned"}
    assert request(environment).status_code == 200
    # A different sibling file is not covered by a file output.
    state["tasks"][0]["result"] = {"protocol":"file","uri":"/data/wf-owned/other.json"}
    assert request(environment).status_code == 403


def test_unauthenticated_preview_never_reads_task_or_content(environment, observed):
    environment.post("/auth/logout")
    assert request(environment).status_code == 401
    assert observed[1] == []


def test_submission_integrity_and_owner_must_match_before_task_read(environment, observed, db):
    row = db.get(ExecutionSubmission,"submitted-owned")
    row.owner_user_id = "other"; db.commit()
    assert request(environment).status_code == 409
    row.owner_user_id = "designer"; row.submitted_sha256 = "invalid"; db.commit()
    assert request(environment).status_code == 409
    assert observed[1] == []


def test_new_deployment_cannot_claim_an_arbitrary_runtime_identity(environment, observed, db):
    before = db.query(Deployment).count()
    result = environment.post("/deployments",json={"workflow_id":"wf-unclaimed-other-user","name":"Claim"})
    assert result.status_code == 409
    assert db.query(Deployment).count() == before
