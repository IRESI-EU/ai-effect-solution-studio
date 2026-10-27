"""Offline local-pilot seed plumbing; this is not wrapper-execution evidence."""
import base64
from copy import deepcopy
import json

import pytest

from app.core.config import settings
from app.schemas.design_ai import AssistantTurn
from app.schemas.workflow_submit import WorkflowSubmitRequest
from app.services import design_ai as service
from app.services.workflow_compiler import compile_to_wp3_payload


def local_policy(monkeypatch):
    # Test-only policy: production catalogue contracts are never modified.
    policies=json.loads(settings.design_ai_templates)
    policies['dutch']['run_input']={'service_id':'dutch-ConfigureAndSynthesize','operation_name':'ConfigureAndSynthesize',
        'evidence_reference':'Offline fixture for local pinned-wrapper policy; no runtime verification claimed',
        'json_schema':{'type':'object','properties':{'seed':{'type':'integer','enum':[42,43]}},
                       'required':['seed'],'additionalProperties':False}}
    monkeypatch.setattr(settings,'design_ai_templates',json.dumps(policies))


@pytest.mark.parametrize('seed',[42,43])
def test_local_seed_proposal_apply_undo_save_reload_builder_compile(environment,db,provider,monkeypatch,seed):
    local_policy(monkeypatch)
    from app.models.solution import Solution
    original=deepcopy(service.content(db.get(Solution,'source-dutch')))
    draft=environment.post('/design-ai/drafts',json={'template_key':'dutch'}).json()
    provider.turn=AssistantTurn(message='Local seed proposal',template_key=None,expected_revision=0,
        edits=[{'kind':'set_run_input','value':json.dumps({'seed':seed}),'node_id':None}])
    def propose(current):
        return environment.post('/design-ai/chat',json={'message':f'Change the generation seed to {seed}.',
            'draft_id':current['id'],'revision':current['revision']}).json()['draft']
    def apply(pending):
        response=environment.post('/design-ai/drafts/'+pending['id']+'/apply',json={
            'revision':pending['revision'],'proposal_id':pending['pending']['id']})
        assert response.status_code==200
        return response.json()
    pending=propose(draft)
    assert pending['design']['run_input'] is None
    current=apply(pending)
    assert current['design']['run_input']=={'seed':seed}
    restored=environment.post('/design-ai/drafts/'+draft['id']+'/undo',json={'revision':current['revision']}).json()
    assert restored['design']==draft['design']
    current=apply(propose(restored))
    saved=environment.post('/design-ai/drafts/'+draft['id']+'/save',json={'revision':current['revision']}).json()['draft']
    # Existing Builder loads this API's design_metadata.run_input into its JSON input.
    reopened=environment.get('/solutions/'+saved['saved_solution_id']).json()
    assert reopened['design_metadata']['run_input']=={'seed':seed}
    nodes=service.service_nodes(reopened['nodes'])
    workflow=WorkflowSubmitRequest(name=reopened['name'],solution_id=reopened['id'],
        nodes=[{'node_id':n['id'],'service_id':n['data']['service']['id'],
                'container_name':n['data']['service']['container_name'],'operation_name':n['data']['service']['operation_name']} for n in nodes],
        edges=[{'source':nodes[0]['id'],'target':nodes[1]['id']}],run_input=reopened['design_metadata']['run_input'])
    compiled=compile_to_wp3_payload(workflow,db)
    assert json.loads(base64.b64decode(compiled['inputs'][0]['uri']))=={'seed':seed}
    assert compiled['inputs'][0]['protocol']=='inline'
    db.expire_all()
    assert service.content(db.get(Solution,'source-dutch'))==original


@pytest.mark.parametrize('value',[{'seed':41},{'seed':44},{'seed':'43'},{'seed':True},{'seed':43,'dataset':'arbitrary.csv'}])
def test_local_seed_policy_rejects_untested_values_and_extra_options(environment,provider,monkeypatch,value):
    local_policy(monkeypatch)
    draft=environment.post('/design-ai/drafts',json={'template_key':'dutch'}).json()
    provider.turn=AssistantTurn(message='Unsupported value',template_key=None,expected_revision=0,
        edits=[{'kind':'set_run_input','value':json.dumps(value),'node_id':None}])
    pending=environment.post('/design-ai/chat',json={'message':'Change the seed','draft_id':draft['id'],'revision':0}).json()['draft']
    assert not pending['pending']['validation']['valid']
    response=environment.post('/design-ai/drafts/'+draft['id']+'/apply',json={'revision':0,'proposal_id':pending['pending']['id']})
    assert response.status_code==422
    current=environment.get('/design-ai/drafts/'+draft['id']).json()
    assert current['revision']==0 and current['design']==draft['design']
