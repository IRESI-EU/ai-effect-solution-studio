"""OFFLINE HTTP integration with deterministic provider doubles, not live validation."""
from copy import deepcopy
import json
import pytest
from app.models.design_ai import DesignDraft
from app.models.operation_contract import OperationContract
from app.models.user import User
from app.schemas.design_ai import AssistantTurn
from app.services import catalogue_discovery as discovery
from test_goal_to_results import qualified, create_copy  # noqa: F401
from test_catalogue_discovery import forbid_network  # noqa: F401


def turn(message,outcome="answer_only",**extra):
    return AssistantTurn(message=message,template_key=None,expected_revision=None,edits=[],
        discovery={"outcome":outcome,**extra.pop("discovery",{})},**extra)


@pytest.mark.parametrize("question",["What does a seed mean?","How do these random settings differ?","What happens when I save?","Which benchmarking capability is available?","How could I use that service?"])
def test_answer_only_explanations_have_no_creation_or_mutation(qualified,question):
    q=qualified
    draft=create_copy(q);state=deepcopy(q["db"].get(DesignDraft,draft["id"]).state)
    q["provider"].turn=turn("OFFLINE answer: a seed controls sample randomness, not quality. Saving stores a design without execution.")
    for scope in ({},{"draft_id":draft["id"],"revision":0}):
        response=q["client"].post("/design-ai/chat",json={"message":question,**scope})
        assert response.status_code==200,response.text
        assert response.json()["message"]==q["provider"].turn.message
        assert response.json()["recommendation"] is None and response.json()["draft"] is None
        q["db"].expire_all();assert q["db"].get(DesignDraft,draft["id"]).state==state
    assert not q["calls"]


@pytest.mark.parametrize("seed,explanation",[(42,"What do the sample numbers mean?"),(43,"Are those choices different benchmark versions?")])
def test_clarification_explanation_single_choice_sequence_retains_context(qualified,seed,explanation):
    q=qualified;client=q["client"];history=[];pending=None
    item=discovery.projection(q["db"],q["db"].get(User,"designer"))["registered_workflows"][0]
    steps=[
        ("Help me choose a sample for the benchmark; ask before selecting.",turn("The generator supplies the benchmark's grid.","clarification_needed",discovery={"question":"Which supported sample seed would you like?"})),
        (explanation,turn("A seed controls randomness in generation; it is not quality or a benchmark version. Different output is not guaranteed.")),
        (str(seed),turn("The chosen sample setting is retained. Review before Create.","supported_recommendation",discovery={"candidate_id":item["candidate_id"]},recommended_seed=seed)),
    ]
    for index,(message,answer) in enumerate(steps):
        q["provider"].turn=answer
        response=client.post("/design-ai/chat",json={"message":message,"history":history,"clarification":pending})
        assert response.status_code==200,response.text
        result=response.json();context=q["provider"].contexts[-1]
        assert context["request"]==message and context["history"]==history
        if pending:assert context["pending_clarification"]==pending
        if index==0:
            assert result["message"]=="The generator supplies the benchmark's grid.\n\nWhich supported sample seed would you like?"
        if index==1:
            assert result["clarification"]==pending and result["question"] is None
            assert result["message"]==answer.message and result["recommendation"] is None
        history += [{"role":"user","content":message},{"role":"assistant","content":result["message"]}]
        pending=result["clarification"]
    assert result["recommendation"]["recommended_seed"]==seed and pending is None
    assert len(q["provider"].contexts)==3  # Exactly one numeric answer, no second attempt.
    assert q["db"].query(DesignDraft).count()==0 and not q["calls"]


def test_declared_default_is_exposed_reviewed_and_never_replaces_explicit_choice(qualified):
    q=qualified;projected=discovery.projection(q["db"],q["db"].get(User,"designer"))
    item=projected["registered_workflows"][0]
    assert item["required_inputs"][0]["default"]==42 and not item["required_inputs"][0]["required"]
    assert next(op for op in projected["operations"] if op["role"]=="source")["settings"][0]["default"]==42
    for supplied,expected in [(None,42),(43,43)]:
        q["provider"].turn=turn("OFFLINE recommend the registered design.","supported_recommendation",discovery={"candidate_id":item["candidate_id"]},recommended_seed=supplied)
        response=q["client"].post("/design-ai/chat",json={"message":"Use the declared sample default." if supplied is None else "Use 43 instead."})
        assert response.status_code==200,response.text
        recommendation=response.json()["recommendation"]
        assert recommendation["recommended_seed"]==expected
        assert recommendation["defaults_used"]==(["seed"] if supplied is None else [])
    contract=q["db"].get(OperationContract,"qualified-synth");definition=deepcopy(contract.definition)
    definition["execution_parameters"]["properties"]["seed"].pop("default")
    contract.definition=definition;q["db"].commit()
    q["provider"].turn=turn("Do not invent a setting.","supported_recommendation",discovery={"candidate_id":item["candidate_id"]})
    assert q["client"].post("/design-ai/chat",json={"message":"Choose a sample."}).status_code==422
    assert q["db"].query(DesignDraft).count()==0


def test_information_and_unsupported_goals_do_not_acquire_workflow_authority(qualified):
    q=qualified
    for request,outcome,answer in [
        ("Is there a benchmark already available?","answer_only","The benchmark requires the generated upstream grid and has no editable settings. Its catalogue-only entry cannot create a standalone design here."),
        ("Dispatch and control live equipment.","no_supported_match","Live control and dispatch are not advertised. No supported match or design was created."),
    ]:
        q["provider"].turn=turn(answer,outcome)
        response=q["client"].post("/design-ai/chat",json={"message":request})
        assert response.status_code==200
        if outcome == "answer_only":
            assert response.json()["message"]==answer
        else:
            assert response.json()["message"]=="No supported catalogue match was found for this request. No design was created or changed."
        assert response.json()["recommendation"] is None and response.json()["draft"] is None
    assert q["db"].query(DesignDraft).count()==0 and not q["calls"]


@pytest.mark.parametrize("injection",[
    {"edits":[{"kind":"rename","value":"mutate","node_id":None}]},
    {"recommended_seed":42},{"template_key":"dutch"},
    {"discovery":{"outcome":"answer_only","candidate_id":"invented"}},
])
def test_answer_only_cannot_smuggle_action_authority(qualified,injection):
    q=qualified
    q["provider"].turn={**turn("Only an answer.").model_dump(),**injection}
    assert q["client"].post("/design-ai/chat",json={"message":"Explain Save."}).status_code==502
    assert q["db"].query(DesignDraft).count()==0


def test_recommendation_still_rechecks_registry_after_provider_completion(qualified):
    q=qualified;item=discovery.projection(q["db"],q["db"].get(User,"designer"))["registered_workflows"][0]
    class ChangingProvider:
        async def respond(self,context):
            c=q["db"].get(OperationContract,"qualified-synth");c.status="withdrawn";q["db"].commit()
            return turn("A stale recommendation.","supported_recommendation",discovery={"candidate_id":item["candidate_id"]},recommended_seed=42)
    from app.main import app
    from app.services.design_ai_provider import get_provider
    original=app.dependency_overrides[get_provider];app.dependency_overrides[get_provider]=lambda:ChangingProvider()
    try:assert q["client"].post("/design-ai/chat",json={"message":"Create a sample design."}).status_code==409
    finally:app.dependency_overrides[get_provider]=original
    assert q["db"].query(DesignDraft).count()==0


def test_clarification_carries_no_authoritative_candidate_and_new_conversation_is_empty(qualified):
    q=qualified;q["provider"].turn=turn("An explanation.")
    bad={"request":"Explain","question":"Which?","candidate_id":"invented"}
    assert q["client"].post("/design-ai/chat",json={"message":"42","clarification":bad}).status_code==422
    assert q["client"].post("/design-ai/chat",json={"message":"A new objective.","history":[],"clarification":None}).status_code==200
    assert q["provider"].contexts[-1]["history"]==[] and "pending_clarification" not in q["provider"].contexts[-1]
