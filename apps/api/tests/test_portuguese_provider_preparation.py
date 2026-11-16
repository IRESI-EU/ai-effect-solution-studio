"""Deterministic transport/validation preparation, never model-interpretation evidence."""
from copy import deepcopy
import json
from pathlib import Path

from conftest import TestProvider
from test_registered_portuguese import registered, create, configure, advertised  # noqa: F401
from test_portuguese_chain import chained  # noqa: F401
from app.main import app
from app.schemas.design_ai import AssistantTurn
from app.services.design_ai_provider import get_provider

CASES=json.loads((Path(__file__).resolve().parents[3]/'deploy/portuguese_sandbox/provider-acceptance-cases-20261116.json').read_text())


def test_frozen_recommendation_has_public_context_and_no_automatic_creation(registered):
    client,_=registered;item=advertised(registered)
    turn=AssistantTurn(message='Registered TrainModel then GenerateData; select the Sandbox test dataset. Defaults are 1 epoch, batch 4 and 10 sequences; execution is disabled.',template_key=None,expected_revision=None,edits=[],discovery={'outcome':'supported_recommendation','candidate_id':item['candidate_id']})
    fake=TestProvider(turn);app.dependency_overrides[get_provider]=lambda:fake
    result=client.post('/design-ai/chat',json={'message':CASES['case_a']['prompt']})
    assert result.status_code==200,result.text
    assert result.json()['draft'] is None and result.json()['recommendation']['candidate_id']==item['candidate_id']
    assert len(fake.contexts)==1
    projection=fake.contexts[0]['catalogue_discovery']['registered_workflows'][0]
    assert projection['registered_operations'][0]['parameters']['properties']['epochs']['default']==1
    assert projection['execution_supported'] is False


def test_frozen_configuration_uses_real_draft_context_and_canonical_validation(registered):
    client,_=registered;draft=create(registered);path='/design-ai/drafts/'+draft['id']
    values={n['id']:n['data']['configuration']['parameters'] for n in draft['design']['nodes']}
    pending=configure(client,draft,settings=values).json()['pending']
    selected=client.post(path+'/apply',json={'revision':0,'proposal_id':pending['id']}).json()
    before=deepcopy(selected['design']);edits=[]
    for node in before['nodes']:
        c=node['data']['configuration'];method=node['data']['service']['operation_name']
        edits.append({'kind':'set_node_parameters','node_id':node['id'],'value':json.dumps({**c,'parameters':{'epochs':2,'batch_size':4} if method=='TrainModel' else {'number_of_examples':20}})})
    fake=TestProvider(AssistantTurn(message='Propose training 2/4 and generation 20; no execution.',template_key=None,expected_revision=1,edits=edits))
    app.dependency_overrides[get_provider]=lambda:fake
    history=[{'role':'user','content':CASES['case_a']['prompt']},{'role':'assistant','content':'Test-double recommendation of the registered Portuguese chain; explicit CSV selection and defaults 1/4/10. No execution.'}]
    response=client.post('/design-ai/chat',json={'draft_id':draft['id'],'revision':1,'message':CASES['case_b']['prompt'],'history':history})
    assert response.status_code==200,response.text
    proposed=response.json()['draft'];assert proposed['revision']==1 and proposed['design']==before
    assert proposed['pending']['validation']['valid']
    assert proposed['pending']['design']['run_input']==before['run_input']
    assert proposed['pending']['design']['edges']==before['edges']
    assert [n['data']['configuration']['parameters'] for n in proposed['pending']['design']['nodes']]==[{'epochs':2,'batch_size':4},{'number_of_examples':20}]
    context=fake.contexts[0];assert context['configuration']['training_input']['selected'] is True
    assert context['history']==history
    assert context['configuration']['supported_edits']==['set_node_parameters']
    serialized=json.dumps(context)
    assert 'approved-data' not in serialized and '/state' not in serialized and 'dataset.csv' not in serialized
    # Invalid returned setting is rejected before replacing the valid pending proposal.
    fake.turn=AssistantTurn.model_validate({**fake.turn.model_dump(),'edits':[edits[0],{**edits[1],'value':json.dumps({**before['nodes'][1]['data']['configuration'],'parameters':{'number_of_examples':21}})}]})
    bad=client.post('/design-ai/chat',json={'draft_id':draft['id'],'revision':1,'message':CASES['case_b']['prompt']})
    assert bad.status_code==422
    assert client.get(path).json()['pending']==proposed['pending']


def test_frozen_ambiguity_preserves_missing_input_and_all_draft_state(registered):
    client,_=registered;draft=create(registered);path='/design-ai/drafts/'+draft['id']
    fake=TestProvider(AssistantTurn(message='Which setting do you mean: training epochs, batch size or generated sequence count? Select a Training CSV before validation.',template_key=None,expected_revision=0,edits=[],discovery={'outcome':'answer_only'}))
    app.dependency_overrides[get_provider]=lambda:fake
    response=client.post('/design-ai/chat',json={'draft_id':draft['id'],'revision':0,'message':CASES['case_c']['prompt']})
    assert response.status_code==200,response.text
    assert response.json()['draft'] is None and len(fake.contexts)==1
    assert fake.contexts[0]['configuration']['training_input']['selected'] is False
    after=client.get(path).json();assert after==draft
    assert 'Select a training CSV before validating.' in after['validation']['errors']
    assert client.post(path+'/save',json={'revision':0}).status_code==422
