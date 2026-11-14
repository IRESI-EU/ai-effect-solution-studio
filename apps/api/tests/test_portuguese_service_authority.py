"""Offline private-wire credential tests; no runtime/provider call."""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.services import orchestrator_adapter as adapter


def test_control_key_only_enters_private_submission_wire(monkeypatch):
    monkeypatch.setattr(adapter.settings, "orchestrator_services_api_key", "offline-test-control-key")
    payload = {"blueprint": {"nodes": []}, "dockerinfo": {}}
    original = deepcopy(payload); calls=[]
    def post(url, **kwargs):
        calls.append(kwargs);return SimpleNamespace(status_code=200,json=lambda:{"workflow_id":"wf-fixture"})
    monkeypatch.setattr(adapter.requests, "post", post)
    assert adapter.submit_to_orchestrator(payload)["workflow_id"]=="wf-fixture"
    assert payload==original and "services_api_key" not in payload
    assert calls[0]["json"]["services_api_key"]=="offline-test-control-key"


def test_default_keeps_legacy_wire_and_conflicts_fail_before_dispatch(monkeypatch):
    monkeypatch.setattr(adapter.settings,"orchestrator_services_api_key","")
    value={"blueprint":{},"dockerinfo":{}}
    assert adapter._service_authorized_payload(value)==value
    monkeypatch.setattr(adapter.settings,"orchestrator_services_api_key","server-control")
    monkeypatch.setattr(adapter.requests,"post",lambda *a,**k:pytest.fail("Must not dispatch"))
    with pytest.raises(HTTPException) as error:
        adapter.submit_to_orchestrator({**value,"services_api_key":"different-control"})
    assert error.value.status_code==409
