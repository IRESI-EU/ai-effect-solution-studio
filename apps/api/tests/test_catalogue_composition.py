"""Synthetic two-operation design logic, not real AI/runtime qualification.

SQLite only. The real provider, runtime probes and submission are forbidden.
"""
from copy import deepcopy
import json
from uuid import uuid4

import pytest

import app.main as main
from app.core.config import settings
from app.models.design_ai import DesignDraft
from app.models.operation_contract import OperationContract
from app.models.service import Service
from app.models.solution import Solution
from app.models.user import User
from app.schemas.design_ai import AssistantTurn
from app.services import catalogue_discovery, catalogue_composition as composition, design_ai_provider
from test_catalogue_discovery import forbid_network  # noqa: F401 -- authenticated stdlib socketpair exception only


@pytest.fixture(autouse=True)
def no_execution_or_real_provider(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Composition must never invoke a real provider, readiness probe or execution")
    for name in ("run_runtime_preflight", "submit_to_orchestrator", "require_binding_transport"):
        monkeypatch.setattr(main, name, forbidden)
    monkeypatch.setattr(design_ai_provider, "AsyncOpenAI", forbidden)


def add_family(db, prefix="synthetic-signal", parameter_required=False):
    services, contracts = [], []
    slot = {"name": "observations", "semantic_concept": f"urn:test:{prefix}:observations", "schema_ref": f"urn:test:{prefix}:schema:1",
        "value_representation": "data_reference", "data_reference_protocols": ["file"], "content_types": ["application/json"],
        "min_cardinality": 1, "max_cardinality": 1}
    for index, role in enumerate(("source", "analyzer")):
        service = Service(id=f"{prefix}-{index}", name=f"Synthetic {prefix} {role}", provider="Test-only catalogue fixture", category=prefix,
            description=f"Declared synthetic {prefix} {role} purpose; not live availability.", input_type="reference", output_type="reference",
            status="approved", lifecycle_status="active", operation_name=f"FixtureOperation{index}", container_name=f"{prefix}-{index}",
            proto_uri="synthetic.proto", image="synthetic:offline", internal_host="unused-test-host", internal_port="8080")
        db.add(service); db.flush()
        spec = {"type": "integer", "title": "Sample count", "description": "Number of synthetic observations.", "required": True, "minimum": 1, "maximum": 10}
        if not parameter_required: spec["default"] = 3
        definition = {"operation_role": role, "binding_transport": "whole-output-v1", "outputs": [deepcopy(slot)],
            "inputs": [] if index == 0 else [{**deepcopy(slot), "required": True, "source_requirement": "upstream_operation"}]}
        if index == 0:
            definition["execution_parameters"] = {"schema_version": "1.0", "transport": "http-parameters-v1", "properties": {"count": spec}}
        contract = OperationContract(id=f"{prefix}-contract-{index}", service_id=service.id,
            operation_identity=f"urn:test:{prefix}:operation:{index}", runtime_operation_name=service.operation_name,
            contract_version="1.0.0", schema_version="1.0", status="active", source_kind="demo", definition=definition)
        db.add(contract); services.append(service); contracts.append(contract)
    db.commit()
    return services, contracts


@pytest.fixture
def catalogue(environment, db, provider, monkeypatch):
    monkeypatch.setattr(settings, "design_ai_templates", "{}")
    db.query(Solution).delete(); db.commit()
    services, contracts = add_family(db)
    return {"client": environment, "db": db, "provider": provider, "services": services, "contracts": contracts}


def candidates(q):
    return catalogue_discovery.projection(q["db"], q["db"].get(User, "designer"))["operation_pairs"]


def recommend(q, choice=None):
    pair = candidates(q)[0]
    q["provider"].turn = AssistantTurn(message="Labelled offline provider double; not intent interpretation.",
        template_key=None, expected_revision=None, edits=[], discovery={"outcome": "supported_recommendation", "candidate_id": pair["candidate_id"]},
        composition_settings=choice)
    response = q["client"].post("/design-ai/chat", json={"message": "Propose a new two-operation synthetic signal study."})
    assert response.status_code == 200, response.text
    return response.json()["recommendation"]


def creation(rec):
    return {k: rec[k] for k in ("candidate_id", "recommendation_revision", "composition_settings", "creation_request_id")}


def create(q):
    rec = recommend(q)
    response = q["client"].post("/design-ai/drafts", json=creation(rec))
    assert response.status_code == 200, response.text
    return rec, response.json()


def test_pair_discovery_and_create_need_no_saved_template(catalogue):
    q = catalogue
    assert q["db"].query(Solution).count() == 0
    rec = recommend(q)
    assert rec["mechanism"] == "catalogue_composed" and not rec["runtime_checked"] and not rec["execution_supported"]
    assert rec["proposed_settings"]["first"] == {"count": 3}
    assert q["db"].query(DesignDraft).count() == q["db"].query(Solution).count() == 0
    created = q["client"].post("/design-ai/drafts", json=creation(rec))
    assert created.status_code == 200, created.text
    draft = created.json()
    assert draft["source"]["kind"] == "catalogue_composed" and "template_key" not in draft
    assert draft["design"]["nodes"] == draft["design"]["edges"] == [] and draft["revision"] == 0
    assert len(draft["pending"]["design"]["nodes"]) == 2 and len(draft["pending"]["design"]["edges"]) == 1
    assert all(n["id"] not in {"first", "second", *[s.id for s in q["services"]]} for n in draft["pending"]["design"]["nodes"])
    assert "composition" not in draft and draft["guided_experiment"] is None
    stored = q["db"].get(DesignDraft, draft["id"])
    assert len(stored.state["composition"]["authority"]["operations"]) == 2


def test_create_apply_full_undo_apply_save_and_reopen_preserve_graph(catalogue):
    q = catalogue; _, draft = create(q); base = f'/design-ai/drafts/{draft["id"]}'
    proposed = deepcopy(draft["pending"]["design"])
    assert q["client"].post(base+"/save", json={"revision": 0}).status_code == 409
    applied = q["client"].post(base+"/apply", json={"revision": 0, "proposal_id": draft["pending"]["id"]})
    assert applied.status_code == 200, applied.text
    assert applied.json()["design"] == proposed
    undone = q["client"].post(base+"/undo", json={"revision": 1}).json()
    assert undone["design"] == draft["design"] and undone["pending"]["design"] == proposed
    assert q["client"].post(base+"/undo", json={"revision": 1}).status_code == 409
    reapplied = q["client"].post(base+"/apply", json={"revision": 2, "proposal_id": undone["pending"]["id"]})
    assert reapplied.status_code == 200 and reapplied.json()["design"] == proposed
    saved = q["client"].post(base+"/save", json={"revision": 3})
    assert saved.status_code == 200, saved.text
    solution_id = saved.json()["draft"]["saved_solution_id"]
    assert q["client"].get(base).json()["design"] == proposed
    solution = q["client"].get(f"/solutions/{solution_id}")
    assert solution.status_code == 200, solution.text
    value = solution.json(); assert value["nodes"] == proposed["nodes"] and value["edges"] == proposed["edges"]
    assert value["design_metadata"]["source"]["kind"] == "catalogue_composed"
    assert value["design_metadata"]["execution_policy"] == "design_only_catalogue_pair"
    assert value["design_metadata"]["composition_authority"] == q["db"].get(DesignDraft, draft["id"]).state["composition"]["authority"]


def test_duplicate_create_apply_undo_and_save_do_not_duplicate_instances(catalogue):
    q = catalogue; rec, draft = create(q); base = f'/design-ai/drafts/{draft["id"]}'
    duplicate = q["client"].post("/design-ai/drafts", json=creation(rec))
    assert duplicate.status_code == 200 and duplicate.json() == draft
    assert q["db"].query(DesignDraft).count() == 1
    body = {"revision": 0, "proposal_id": draft["pending"]["id"]}
    assert q["client"].post(base+"/apply", json=body).status_code == 200
    assert q["client"].post(base+"/apply", json=body).status_code == 409
    assert q["client"].post(base+"/save", json={"revision": 1}).status_code == 200
    assert q["client"].post(base+"/save", json={"revision": 1}).status_code == 200
    assert q["db"].query(Solution).count() == 1


def test_second_family_needs_no_country_or_operation_specific_logic(catalogue):
    q = catalogue
    add_family(q["db"], "synthetic-images")
    pairs = candidates(q)
    assert {p["steps"][0]["title"].split()[1] for p in pairs} == {"synthetic-signal", "synthetic-images"}
    assert all(p["kind"] == "catalogue_composed" for p in pairs)


@pytest.mark.parametrize("change", ["missing", "withdrawn", "ambiguous", "no_transport", "external_input", "multiple_slots", "schema", "semantic", "representation", "protocol", "format", "cardinality", "missing_runtime_metadata"])
def test_incomplete_unsupported_ambiguous_or_incompatible_pairs_are_not_advertised(catalogue, change):
    q = catalogue; db = q["db"]; first, second = q["contracts"]; value = deepcopy(second.definition)
    if change == "missing": db.delete(second)
    elif change == "withdrawn": second.status = "withdrawn"
    elif change == "ambiguous":
        db.add(OperationContract(id="ambiguous-contract", service_id=second.service_id, operation_identity="urn:test:ambiguous", runtime_operation_name=second.runtime_operation_name,
            contract_version="2.0.0", status="active", source_kind="demo", definition=value))
    elif change == "no_transport": value["binding_transport"] = None; second.definition = value
    elif change == "external_input":
        a=deepcopy(first.definition); a["inputs"]=[{**deepcopy(value["inputs"][0]), "source_requirement":"workflow_input"}];first.definition=a
    elif change == "multiple_slots": value["inputs"].append({**value["inputs"][0], "name":"another"}); second.definition=value
    elif change == "missing_runtime_metadata": q["services"][0].proto_uri = ""
    else:
        key, field = {"schema":("schema_ref","urn:test:wrong:2"),"semantic":("semantic_concept","unrelated"),"representation":("value_representation","structured_object"),
            "protocol":("data_reference_protocols",["https"]),"format":("content_types",["text/csv"]),"cardinality":("max_cardinality",2)}[change]
        value["inputs"][0][key] = field; second.definition=value
    db.commit(); assert not candidates(q)
    assert db.query(DesignDraft).count() == 0


@pytest.mark.parametrize("change", ["hidden", "archived", "rejected", "adapter"])
def test_unauthorized_or_adapter_operations_cannot_compose(catalogue, change):
    q = catalogue; source = q["services"][0]
    if change == "hidden": source.status="validated"; source.created_by_user_id="other"
    elif change == "archived": source.lifecycle_status="archived"
    elif change == "rejected": source.status="rejected"
    else: source.orchestration_mode="adapter"; source.adapter_type="new-adapter"
    q["db"].commit(); assert not candidates(q)


def test_missing_required_setting_clarifies_and_no_default_is_invented(catalogue):
    q = catalogue; contract=q["contracts"][0]; value=deepcopy(contract.definition);value["execution_parameters"]["properties"]["count"].pop("default");contract.definition=value;q["db"].commit()
    pair=candidates(q)[0];assert pair["unresolved_requirements"]==[{"step":"first","name":"count","title":"Sample count"}]
    q["provider"].turn=AssistantTurn(message="Offline clarification",template_key=None,expected_revision=None,edits=[],discovery={"outcome":"clarification_needed","question":"What sample count should the first operation use (1 to 10)?"})
    response=q["client"].post("/design-ai/chat",json={"message":"Create a new study."})
    assert response.status_code==200 and response.json()["recommendation"] is None
    assert q["db"].query(DesignDraft).count()==0
    q["provider"].turn=AssistantTurn(message="Offline missing-value double",template_key=None,expected_revision=None,edits=[],discovery={"outcome":"supported_recommendation","candidate_id":pair["candidate_id"]})
    assert q["client"].post("/design-ai/chat",json={"message":"Create a study."}).status_code==422
    rec=recommend(q,{"first":[{"name":"count","value":7}],"second":[]})
    assert rec["proposed_settings"]["first"]=={"count":7}


@pytest.mark.parametrize("assignments", [[{"name":"count","value":0}],[{"name":"count","value":True}],[{"name":"invented","value":1}],[{"name":"count","value":2},{"name":"count","value":4}]])
def test_required_settings_use_registry_validation(catalogue, assignments):
    q=catalogue;pair=candidates(q)[0]
    q["provider"].turn=AssistantTurn(message="Offline invalid settings",template_key=None,expected_revision=None,edits=[],discovery={"outcome":"supported_recommendation","candidate_id":pair["candidate_id"]},composition_settings={"first":assignments,"second":[]})
    assert q["client"].post("/design-ai/chat",json={"message":"Propose a study."}).status_code==422
    assert q["db"].query(DesignDraft).count()==0


@pytest.mark.parametrize("phase", ["create","apply","save"])
@pytest.mark.parametrize("change", ["catalogue","contract","authorization"])
def test_stale_authority_is_rejected_without_mutation(catalogue, phase, change):
    q=catalogue;rec=recommend(q);draft=None
    if phase!="create":
        draft=q["client"].post("/design-ai/drafts",json=creation(rec)).json();base=f'/design-ai/drafts/{draft["id"]}'
        if phase=="save":assert q["client"].post(base+"/apply",json={"revision":0,"proposal_id":draft["pending"]["id"]}).status_code==200
    if change=="catalogue":q["services"][0].image="changed:unreviewed"
    elif change=="contract":c=q["contracts"][0];c.definition={**c.definition,"compatibility_notes":["Changed after review"]}
    else:q["services"][0].status="validated";q["services"][0].created_by_user_id="other"
    q["db"].commit()
    if phase=="create":response=q["client"].post("/design-ai/drafts",json=creation(rec))
    elif phase=="apply":response=q["client"].post(base+"/apply",json={"revision":0,"proposal_id":draft["pending"]["id"]})
    else:response=q["client"].post(base+"/save",json={"revision":1})
    assert response.status_code in {409,422}
    assert q["db"].query(Solution).count()==0
    if draft:q["db"].expire_all();assert q["db"].get(DesignDraft,draft["id"]).revision==(1 if phase=="save" else 0)


def test_no_provider_graph_instance_or_endpoint_can_be_supplied(catalogue):
    q=catalogue;pair=candidates(q)[0]
    q["provider"].turn={"message":"Labelled invalid double","template_key":None,"expected_revision":None,"edits":[],
        "discovery":{"outcome":"supported_recommendation","candidate_id":pair["candidate_id"]},
        "composition_settings":{"first":[],"second":[],"nodes":[{"id":"model-instance","endpoint":"http://do-not-fetch.invalid"}]}}
    assert q["client"].post("/design-ai/chat",json={"message":"Create a study."}).status_code==502
    q["provider"].turn={"message":"Invented double","template_key":None,"expected_revision":None,"edits":[],"discovery":{"outcome":"supported_recommendation","candidate_id":"pair-invented"}}
    assert q["client"].post("/design-ai/chat",json={"message":"Create a study."}).status_code==422
    assert q["db"].query(DesignDraft).count()==0


def test_new_composition_has_no_execution_or_qualification_path(catalogue, monkeypatch):
    q=catalogue;_,draft=create(q);base=f'/design-ai/drafts/{draft["id"]}'
    q["client"].post(base+"/apply",json={"revision":0,"proposal_id":draft["pending"]["id"]})
    saved=q["client"].post(base+"/save",json={"revision":1}).json()["draft"]
    from app.services import qualified_demo
    monkeypatch.setattr(qualified_demo,"profile_enabled",lambda:True)
    assert q["client"].post(base+"/execution-review",json={"revision":1}).status_code==422
    design=saved["design"]
    body={"name":design["name"],"solution_id":saved["saved_solution_id"],"nodes":[{"node_id":n["id"],"service_id":n["data"]["service"]["id"],"container_name":n["data"]["service"]["container_name"],
        "operation_name":n["data"]["service"]["operation_name"],**{k:n["data"][k] for k in ("configuration","operation_contract") if k in n["data"]}} for n in design["nodes"]],
        "edges":[{"source":e["source"],"target":e["target"],"binding":e["data"]["binding"]} for e in design["edges"]]}
    for path in ("/workflows/runtime-preflight","/workflows/submit-to-orchestrator"):
        response=q["client"].post(path,json=body);assert response.status_code==403,response.text


def test_stale_save_and_provenance_stripping_cannot_overwrite_or_unlock(catalogue):
    q=catalogue;_,draft=create(q);base=f'/design-ai/drafts/{draft["id"]}'
    q["client"].post(base+"/apply",json={"revision":0,"proposal_id":draft["pending"]["id"]})
    saved=q["client"].post(base+"/save",json={"revision":1}).json()["draft"]
    path=f'/solutions/{saved["saved_solution_id"]}';solution=q["client"].get(path).json()
    rejected=q["client"].put(path,json={"expected_updated_at":solution["updated_at"],"name":"Do not retain this mutation","design_metadata":{"source":{"kind":"registered_workflow"}}})
    assert rejected.status_code==409
    assert q["client"].get(path).json()["name"]==solution["name"]
    updated=q["client"].put(path,json={"expected_updated_at":solution["updated_at"],"name":"Edited in the disposable Builder copy"})
    assert updated.status_code==200,updated.text
    assert q["client"].post(base+"/save",json={"revision":1}).status_code==409
    assert q["client"].get(path).json()["name"]=="Edited in the disposable Builder copy"
    assert q["db"].query(Solution).count()==1


def test_creation_nonce_cannot_be_reused_for_another_settings_choice(catalogue):
    q=catalogue;rec,draft=create(q);body=creation(rec)
    body["composition_settings"]={"first":[{"name":"count","value":9}],"second":[]}
    assert q["client"].post("/design-ai/drafts",json=body).status_code==409
    assert q["db"].query(DesignDraft).count()==1
    assert q["client"].get(f'/design-ai/drafts/{draft["id"]}').json()["pending"]["design"]==draft["pending"]["design"]


def test_pair_authorization_is_rechecked_after_provider_wait(catalogue):
    q=catalogue;pair=candidates(q)[0]
    q["provider"].turn=AssistantTurn(message="Offline revoked pair",template_key=None,expected_revision=None,edits=[],discovery={"outcome":"supported_recommendation","candidate_id":pair["candidate_id"]})
    original=q["provider"].respond
    async def revoke(context):
        result=await original(context);q["services"][0].status="rejected";q["db"].commit();return result
    q["provider"].respond=revoke
    assert q["client"].post("/design-ai/chat",json={"message":"Create a new study."}).status_code==409
    assert q["db"].query(DesignDraft).count()==0


def test_ambiguous_target_clarifies_without_creating(catalogue):
    q=catalogue;pair=candidates(q)[0]
    q["provider"].turn=AssistantTurn(message="Offline ambiguous target",template_key=None,expected_revision=None,edits=[],discovery={"outcome":"clarification_needed","question":"Which approved analyzer should receive the generated observations?"})
    response=q["client"].post("/design-ai/chat",json={"message":"Connect the generator to an analyzer."})
    assert response.status_code==200 and response.json()["recommendation"] is None
    assert "Which approved analyzer" in response.json()["question"] and q["db"].query(DesignDraft).count()==0


def test_no_supported_pair_is_an_honest_no_match(catalogue):
    q=catalogue;q["contracts"][1].status="withdrawn";q["db"].commit()
    q["provider"].turn=AssistantTurn(message="Offline unsupported pair",template_key=None,expected_revision=None,edits=[],discovery={"outcome":"no_supported_match"})
    response=q["client"].post("/design-ai/chat",json={"message":"Create a new study."})
    assert response.status_code==200 and response.json()["outcome"]=="no_supported_match"
    assert response.json()["recommendation"] is None and not q["provider"].contexts[-1]["catalogue_discovery"]["operation_pairs"]


def test_explanations_are_scoped_and_cannot_expand_new_draft(catalogue):
    q=catalogue;_,draft=create(q);base=f'/design-ai/drafts/{draft["id"]}'
    q["provider"].turn=AssistantTurn(message="Offline explanation: design only, not executed.",template_key=None,expected_revision=0,edits=[])
    response=q["client"].post("/design-ai/chat",json={"draft_id":draft["id"],"revision":0,"message":"Explain the proposal and whether it executed."})
    assert response.status_code==200
    context=q["provider"].contexts[-1]
    assert context["configuration"]["source_kind"]=="catalogue_composed" and context["configuration"]["supported_edits"]==[]
    assert all(forbidden not in json.dumps(context) for forbidden in ("template_key","internal_host","unused-test-host","proto_uri"))
    # Use a dictionary to exercise the actual strict parsing boundary.
    q["provider"].turn={**q["provider"].turn.model_dump(),"edits":[{"kind":"rename","node_id":None,"value":"Not allowed in this scope"}]}
    assert q["client"].post("/design-ai/chat",json={"draft_id":draft["id"],"revision":0,"message":"Rename and expand it."}).status_code==422
    assert q["client"].get(base).json()["design"]==draft["design"]


def test_other_owner_cannot_read_apply_or_save(catalogue):
    from app.main import app
    from app.routers.design_ai import pilot_user
    q=catalogue;_,draft=create(q);base=f'/design-ai/drafts/{draft["id"]}'
    app.dependency_overrides[pilot_user]=lambda:q["db"].get(User,"other")
    try:
        assert q["client"].get(base).status_code==404
        assert q["client"].post(base+"/apply",json={"revision":0,"proposal_id":draft["pending"]["id"]}).status_code==404
        assert q["client"].post(base+"/save",json={"revision":0}).status_code==404
    finally:app.dependency_overrides.pop(pilot_user)


@pytest.mark.parametrize("outcome", ["clarification_needed", "no_supported_match"])
def test_discovery_nonrecommendation_preserves_existing_pending_copy(catalogue, outcome):
    q=catalogue;_,draft=create(q);base=f'/design-ai/drafts/{draft["id"]}'
    before=q["client"].get(base).json()
    q["provider"].turn=AssistantTurn(message="Labelled offline response",template_key=None,expected_revision=None,edits=[],
        discovery={"outcome":outcome,**({"question":"Which observations should be analyzed?"} if outcome=="clarification_needed" else {})})
    response=q["client"].post("/design-ai/chat",json={"message":"Analyze my data."})
    assert response.status_code==200
    assert response.json()["recommendation"] is None and response.json()["draft"] is None
    assert q["client"].get(base).json()==before
    assert q["db"].query(DesignDraft).count()==1 and q["db"].query(Solution).count()==0


def test_withdrawn_contract_rejects_apply_and_preserves_full_proposal(catalogue):
    q=catalogue;_,draft=create(q);base=f'/design-ai/drafts/{draft["id"]}'
    stored=q["db"].get(DesignDraft,draft["id"]);before=deepcopy(stored.state)
    q["contracts"][1].status="withdrawn";q["db"].commit()
    response=q["client"].post(base+"/apply",json={"revision":0,"proposal_id":draft["pending"]["id"]})
    assert response.status_code in {409,422}
    q["db"].expire_all();stored=q["db"].get(DesignDraft,draft["id"])
    assert stored.revision==0 and stored.state==before
    assert q["db"].query(Solution).count()==0


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_settings_are_rejected_before_fingerprinting(value):
    from pydantic import ValidationError
    from app.schemas.design_ai import SettingAssignment
    with pytest.raises(ValidationError, match="finite"):
        SettingAssignment(name="count", value=value)


def test_pair_changed_between_projection_and_resolution_is_rejected(catalogue, monkeypatch):
    q=catalogue;pair=candidates(q)[0]
    q["provider"].turn=AssistantTurn(message="Offline race double",template_key=None,expected_revision=None,edits=[],discovery={"outcome":"supported_recommendation","candidate_id":pair["candidate_id"]})
    original=composition.resolve
    def changed(*args, **kwargs):
        record=original(*args, **kwargs)
        return {**record,"revision":"0"*64}
    monkeypatch.setattr(composition,"resolve",changed)
    assert q["client"].post("/design-ai/chat",json={"message":"Propose a study."}).status_code==409
    assert q["db"].query(DesignDraft).count()==0


def test_private_runtime_reference_cannot_be_a_string_setting(catalogue):
    q=catalogue;c=q["contracts"][0];value=deepcopy(c.definition)
    value["execution_parameters"]["properties"]={"mode":{"type":"string","title":"Mode","description":"Test-only choice","enum":["unused-test-host"],"default":"unused-test-host"}}
    c.definition=value;q["db"].commit()
    assert candidates(q)==[]


def test_legacy_guided_settings_cannot_mutate_a_composed_draft(catalogue):
    q=catalogue;_,draft=create(q);base=f'/design-ai/drafts/{draft["id"]}'
    response=q["client"].post(base+"/guided-settings",json={"revision":0,"seed":43})
    assert response.status_code==422
    assert q["client"].get(base).json()["design"]==draft["design"]
