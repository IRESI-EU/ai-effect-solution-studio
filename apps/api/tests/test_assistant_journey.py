"""Full saved-solution conversation with explicit offline provider responses."""
from copy import deepcopy
import json
from pathlib import Path

from app.db import SessionLocal
from app.models.execution_submission import ExecutionSubmission
from app.models.operation_contract import OperationContract
from app.models.service import Service
from app.schemas.design_ai import AssistantTurn, SolutionEdit
from app.schemas.solution_assistant import SavedSolutionResponse, EditBase
from test_saved_solution_assistant import bound, turn, scope, apply, chat


def send(client, solution, provider, message):
    state=client.get(scope(solution)).json()
    # Explicit offline fixture adapter: bind placeholder fixtures to the actual
    # advertised saved base. Real model-path tests supply their exact base/refs.
    if isinstance(getattr(provider, 'turn', None), SavedSolutionResponse) and provider.turn.edit_base and provider.turn.edit_base.expected_updated_at == 'FIXTURE-BIND-BEFORE-SEND':
        from datetime import datetime
        from types import SimpleNamespace
        from app.services.solution_assistant import target_ref
        actual = client.get('/solutions/' + solution['id']).json()
        base = SimpleNamespace(id=solution['id'], updated_at=datetime.fromisoformat(state['expected_updated_at']))
        refs = {n['id']:target_ref(base, n['id']) for n in actual['nodes'] if n.get('data', {}).get('service')}
        value = provider.turn.model_dump()
        value['edit_base'] = {'kind':'saved', 'expected_updated_at':state['expected_updated_at'], 'conversation_revision':state['conversation_revision'], 'proposal_id':None, 'candidate_sha256':None}
        for edit in value['solution_edits']:
            if edit['node_id'] in refs: edit['node_id'] = refs[edit['node_id']]
            if edit['kind'] in ('connect','disconnect'):
                data = json.loads(edit['value'])
                for key in ('source','target'): data[key] = refs.get(data.get(key), data.get(key))
                edit['value'] = json.dumps(data)
        provider.turn = provider.turn.model_copy(update={'edit_base':EditBase.model_validate(value['edit_base']),'solution_edits':[SolutionEdit.model_validate(e) for e in value['solution_edits']]})
    return client.post(scope(solution)+'/chat',json={'message':message,**{k:state[k] for k in ('expected_updated_at','conversation_revision')}})


def test_fresh_goal_clarification_connected_follow_up_add_and_compatible_replace(bound,provider):
    client,_=bound
    with SessionLocal() as db:
        target=db.get(Service,'portugal-ActualC'); template=db.get(OperationContract,'sink')
        db.add(OperationContract(id='alternative',service_id=target.id,status='active',operation_identity='urn:test:alternative',runtime_operation_name=target.operation_name,
            contract_version='1.0.0',schema_version='1.0',source_kind='manual',definition=deepcopy(template.definition)))
        db.commit()
    response=client.post('/solutions',json={'name':'Fresh goal','nodes':[],'edges':[],
        'design_metadata':{'run_input':None,'assistant_goal':'Compare synthetic grid reports'}})
    solution=response.json();identifier=solution['id']
    provider.turn=turn(message='I found the published grid generator and report services.', outcome='clarification', clarification='Which report view do you want?')
    state=send(client,solution,provider,'Compare synthetic grid reports').json()
    assert state['clarification']['question']=='Which report view do you want?'
    assert state['pending'] is None
    assert state['catalogue_used']['total_accessible']>0
    assert provider.contexts[-1]['catalogue']['compatible_connections']
    # An explanatory detour retains the pending question and changes no graph.
    provider.turn=turn(message='The published report consumes the generated grid reference.')
    send(client,solution,provider,'Explain the connection first')
    assert provider.contexts[-1]['pending_clarification']['question']=='Which report view do you want?'
    assert client.get('/solutions/'+identifier).json()==solution
    edits=[{'kind':'add_service','value':json.dumps({'service_id':sid,'local_ref':ref})} for sid,ref in
        [('dutch-ConfigureAndSynthesize','producer'),('dutch-RunBenchmark','report')]]
    edits.append({'kind':'connect','value':json.dumps({'source':'producer','target':'report','source_slot':'grid','target_slot':'grid'})})
    proposed=chat(client,solution,provider,edits,message='Use the normal report').json()
    assert proposed['clarification'] is None
    assert apply(client,solution,proposed).status_code==200
    current=client.get('/solutions/'+identifier).json();producer=current['nodes'][0]['id'];report=current['nodes'][1]['id']
    assert len(current['nodes'])==4 and len(current['edges'])==3
    assert {n['type'] for n in current['nodes'] if not n['data'].get('service')}=={'input','output'}
    # Follow-up edits use the current logical instance, then a compatible add.
    edit=chat(client,current,provider,[{'kind':'set_node_label','node_id':report,'value':'Primary report'}]).json()
    assert apply(client,current,edit).status_code==200
    current=client.get('/solutions/'+identifier).json()
    additions=[{'kind':'add_service','value':json.dumps({'service_id':'dutch-RunBenchmark','local_ref':'second'})},
        {'kind':'connect','value':json.dumps({'source':producer,'target':'second','source_slot':'grid','target_slot':'grid'})}]
    proposed=chat(client,current,provider,additions).json()
    assert apply(client,current,proposed).status_code==200
    current=client.get('/solutions/'+identifier).json();second=current['nodes'][-1]['id'];old_edges=deepcopy(current['edges'])
    proposed=chat(client,current,provider,[{'kind':'replace_service','node_id':second,'value':'{"service_id":"portugal-ActualC"}'}]).json()
    assert any(r['service_id']=='portugal-ActualC'
        for r in provider.contexts[-1]['compatible_actions']['replacements'])
    assert apply(client,current,proposed).status_code==200
    final=client.get('/solutions/'+identifier).json()
    assert final['id']==identifier and len(final['nodes'])==5 and final['edges']==old_edges
    assert final['nodes'][-1]['id']==second and final['nodes'][-1]['data']['service']['id']=='portugal-ActualC'
    assert final['design_metadata']==solution['design_metadata']
    with SessionLocal() as db:assert db.query(ExecutionSubmission).count()==0


def test_clarification_cannot_smuggle_changes_or_erase_review(bound,provider):
    client,_=bound
    solution=client.post('/solutions',json={'name':'Clarification guard','nodes':[],'edges':[]}).json()
    old=chat(client,solution,provider,[{'kind':'rename','value':'Already reviewed'}]).json()
    provider.turn=turn([{'kind':'rename','value':'Unreviewed'}])
    provider.turn.outcome='clarification'
    provider.turn.clarification='Which one?'
    response=send(client,solution,provider,'Clarify')
    assert response.status_code==502
    assert client.get(scope(solution)).json()==old


def test_retrieval_ranks_late_relevant_service_and_excludes_inaccessible_drafts(bound,provider):
    client,_=bound
    with SessionLocal() as db:
        for index in range(45):
            db.add(Service(id='retrieval-'+str(index),name='A generic '+str(index),provider='Fixture',category='fixture',
                description='Unrelated software',input_type='JSON',output_type='JSON',operation_name='Inspect',status='approved',lifecycle_status='active'))
        for identifier,status,lifecycle in [('late','approved','active'),('draft','draft','active'),('hidden','validated','active'),('archived','approved','archived')]:
            db.add(Service(id=identifier,name='Z relevant heatwave frequency '+identifier,provider='Fixture',category='fixture',
                description='Heatwave frequency estimator',input_type='JSON',output_type='JSON',operation_name='Inspect',status=status,lifecycle_status=lifecycle,created_by_user_id='other'))
        db.commit()
    solution=client.post('/solutions',json={'name':'Goal','nodes':[],'edges':[],
        'design_metadata':{'assistant_goal':'heatwave frequency'}}).json()
    provider.turn=turn(message='Retrieved current catalogue')
    assert send(client,solution,provider,'Which estimator fits?').status_code==200
    catalogue=provider.contexts[-1]['catalogue'];identifiers=[c['service_id'] for c in catalogue['services']]
    assert catalogue['truncated'] and len(identifiers)==40 and identifiers[0]=='late'
    assert not {'draft','hidden','archived'}&set(identifiers)


def test_recorded_failed_genuine_reply_preserves_review_without_inventing_clarification(bound,provider):
    """Actual failed response replay only; no inference or successful live claim."""
    client,_=bound
    solution=client.post('/solutions',json={'name':'Recorded failure replay','nodes':[],'edges':[]}).json()
    pending=chat(client,solution,provider,[{'kind':'rename','value':'Existing reviewed proposal'}]).json()
    recorded=json.loads((Path(__file__).parent/'fixtures/genuine-clarification-miss-20261119.json').read_text(encoding='utf-8'))
    # Historical legacy response is translated explicitly into an answer fixture;
    # the live focused provider must never accept old response fields as fallback.
    historical=AssistantTurn.model_validate(recorded)
    provider.turn=SavedSolutionResponse(outcome='answer', message=historical.message,
        clarification=None, solution_edits=[], assumptions=[])
    response=send(client,solution,provider,'Recorded failed comparison goal replay')
    assert response.status_code==200
    actual=response.json()
    assert actual['messages'][-1]['content']==recorded['message']
    assert actual['clarification'] is None and actual['pending']==pending['pending']
    assert client.get('/solutions/'+solution['id']).json()==solution
    with SessionLocal() as db:assert db.query(ExecutionSubmission).count()==0
