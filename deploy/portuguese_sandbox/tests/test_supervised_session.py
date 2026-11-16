"""Activation uses fake lifecycle tools; no Docker, live authority or algorithms."""
import importlib.util
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location("pt_session",Path(__file__).parents[1]/"supervised_session.py")
session=importlib.util.module_from_spec(spec);spec.loader.exec_module(session)


class Driver:
    def __init__(self, faults=None):
        self.calls=[];self.api=False;self.adapter="stable";self.waiting=False
        self.faults=list(faults or []);self.started=0;self.authorities=0;self.jobs=0
    def verify_authority(self): self.calls.append("existing-authority")
    def configure_adapter(self):
        assert not self.api;self.calls.append("configure-adapter")
    def up(self, role):
        assert role in {"api","pt-adapter"};self.calls.append("up-"+role)
        if role=="pt-adapter": assert not self.waiting and not self.api
    def probe(self, *, timeout=20):
        assert not self.api and not self.waiting;self.calls.append("GET-only-probe")
        if self.faults: raise self.faults.pop(0)
    def identity(self, _): return self.adapter
    def start_worker(self):
        assert not self.api;self.calls.append("start-once");self.started+=1;self.waiting=True
    def wait_lease(self): assert self.waiting;self.calls.append("fresh-lease")
    def enable_api(self): assert self.waiting;self.api=True;self.calls.append("enable-api")
    def disable_api(self): self.api=False;self.calls.append("disable-api")
    def stop_if_unbound(self): self.waiting=False;self.calls.append("stop-unbound")


def test_exact_activation_order_keeps_adapter_and_waiting_processor_stable():
    d=Driver();session.activate(d)
    assert d.calls==["existing-authority","configure-adapter","up-pt-adapter","GET-only-probe","start-once","fresh-lease","enable-api","up-api","fresh-lease"]
    assert d.started==1 and d.waiting and d.api
    assert d.authorities==d.jobs==0


def test_transient_probe_recovery_precedes_worker_and_api():
    d=Driver([ConnectionError("DNS"),ConnectionError("Connection startup")])
    session.activate(d,sleep=lambda _:None)
    assert d.calls.count("GET-only-probe")==3 and d.started==1
    assert d.calls.index("start-once")>d.calls.index("GET-only-probe")
    assert d.authorities==d.jobs==0


def test_startup_deadline_and_permanent_mismatch_never_start_processor():
    d=Driver([ConnectionError("DNS")]);clock=iter([0,31])
    with pytest.raises(ValueError,match="deadline"):
        session.activate(d,monotonic=lambda:next(clock))
    assert d.started==0 and not d.api
    d=Driver([ValueError("Authentication/capability mismatch")])
    with pytest.raises(ValueError,match="mismatch"):session.activate(d)
    assert d.calls.count("GET-only-probe")==1 and d.started==0 and not d.api


def test_absent_authority_stops_before_configuration_change():
    d=Driver()
    def deny():raise ValueError("Closed authority")
    d.verify_authority=deny
    with pytest.raises(ValueError,match="Closed"):session.activate(d)
    assert not d.calls and d.started==0 and not d.api


def test_lost_processor_lease_disables_admission_without_replacement():
    d=Driver()
    def fail():raise ValueError("Processor finished")
    d.wait_lease=fail
    with pytest.raises(ValueError,match="finished"):session.activate(d)
    assert d.started==1 and not d.api and not d.waiting
    assert "up-pt-adapter"==d.calls[2] and d.calls.count("up-pt-adapter")==1


def test_unexpected_adapter_recreation_rolls_back_api_without_second_worker():
    d=Driver();original=d.up
    def up(role):
        original(role)
        if role=="api":d.adapter="changed"
    d.up=up
    with pytest.raises(ValueError,match="identity changed"):session.activate(d)
    assert not d.api and d.started==1 and not d.waiting


def test_api_flag_change_only_touches_api_and_preserves_backup(tmp_path):
    d=session.DockerProfile.__new__(session.DockerProfile)
    d.config={"services":{"api":{"environment":{"PRIVATE":"retained"}},"pt-adapter":{"image":"retained"},"ml":{"image":"original"}}}
    d.authority={"authorization_id":"OFFLINE-test"};d.path=tmp_path/"compose.json"
    d.original=b'{"retained":true}';d.path.write_bytes(d.original)
    d.enable_api()
    assert d.config["services"]["pt-adapter"]=={"image":"retained"}
    assert d.config["services"]["ml"]=={"image":"original"}
    assert d.config["services"]["api"]["environment"]["PRIVATE"]=="retained"
    d.path.write_bytes(b"concurrent change")
    with pytest.raises(ValueError,match="changed concurrently"):d.disable_api()


def test_restore_refuses_unrelated_configuration_and_never_changes_database():
    from copy import deepcopy
    before={"name":"original","volumes":{"db":{}},"services":{"api":{"mode":False},"pt-adapter":{},"chain-worker":{},"postgres":{"image":"original"}}}
    active=deepcopy(before);active["services"]["api"]["mode"]=True
    assert session.reviewed_restore(active,before)==before
    active["services"]["postgres"]["image"]="unexpected"
    with pytest.raises(ValueError,match="Unrelated service drift"):session.reviewed_restore(active,before)
    active=deepcopy(before);active["volumes"]["db"]={"name":"other"}
    with pytest.raises(ValueError,match="Unrelated compose"):session.reviewed_restore(active,before)
