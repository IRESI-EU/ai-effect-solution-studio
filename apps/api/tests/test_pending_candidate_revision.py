"""Successful normal transitions with explicit OFFLINE replies; no paid model or Run."""
from copy import deepcopy
import json
import pytest
from app.main import app
from app.db import SessionLocal
from app.models.operation_contract import OperationContract
from app.models.execution_submission import ExecutionSubmission
from app.schemas.solution_assistant import SavedSolutionResponse
from app.services.design_ai_provider import get_provider
from test_saved_solution_assistant import bound, scope, apply
from test_capability_bindings import workflow


class Offline:
    name = 'EXPLICIT OFFLINE PENDING REVISION FIXTURE'
    mode = 'test'
    def __init__(self): self.plan = None; self.contexts = []
    async def respond(self, context):
        self.contexts.append(deepcopy(context))
        return SavedSolutionResponse.model_validate(self.plan(context))


@pytest.fixture
def journey(bound):
    client, _ = bound
    with SessionLocal() as db:
        source = db.get(OperationContract, 'source')
        d = deepcopy(source.definition)
        d['execution_parameters'] = {'schema_version':'1.0','transport':'http-parameters-v1','properties':{'count':{'type':'integer','title':'Fixture candidate maximum','description':'Synthetic bounded test fixture','minimum':1,'maximum':4,'default':1}}}
        source.definition = d
        sink = db.get(OperationContract, 'sink')
        db.add(OperationContract(id='alternate', service_id='portugal-ActualC', status='active',
            operation_identity='urn:test:alternate', runtime_operation_name='ActualC', contract_version='1.0.0',
            schema_version='1.0', source_kind='manual', definition=deepcopy(sink.definition)))
        db.commit()
    provider = Offline(); app.dependency_overrides[get_provider] = lambda:provider
    solution = client.post('/solutions',json={'name':'Pending revision fixture','nodes':[],'edges':[],
        'design_metadata':{'run_input':None}}).json()
    return client, solution, provider


def ask(journey, plan, text='EXPLICIT OFFLINE design action'):
    client, solution, provider = journey; provider.plan = plan
    state = client.get(scope(solution)).json()
    return client.post(scope(solution)+'/chat',json={'message':text,**{k:state[k] for k in ('expected_updated_at','conversation_revision')}})


def reply(context, edits=(), base='pending', assumptions=()):
    return dict(outcome='proposal' if edits else 'answer', message='EXPLICIT OFFLINE review; nothing is applied or run.',
        clarification=None, assumptions=list(assumptions), solution_edits=list(edits),
        edit_base=context['edit_bases'][base] if edits else None)


def addition(service, ref): return dict(kind='add_service',value=json.dumps(dict(service_id=service,local_ref=ref)))
def link(source, target): return dict(kind='connect',value=json.dumps(dict(source=source,target=target,source_slot='grid',target_slot='grid')))
def parameter(ref, count): return dict(kind='set_node_parameters',node_id=ref,value=json.dumps(dict(count=count)))


def create(journey):
    r=ask(journey,lambda c:reply(c,[addition('dutch-ConfigureAndSynthesize','source'),addition('dutch-RunBenchmark','view'),link('source','view')],base='saved',assumptions=['OFFLINE fixture view selected for review; no published view default.']))
    assert r.status_code==200,r.text
    return r.json()


def steps(state): return state['pending']['candidate']['steps']
def by_service(context, service): return next(s for s in context['pending_candidate']['steps'] if s['service_id']==service)


def test_cumulative_revision_confirmation_replace_reopen_apply_saved_edit_undo(journey):
    client, solution, provider = journey
    first=create(journey); first_ids=[s['node_id'] for s in steps(first)]
    assert len(first_ids)==2 and len(first['pending']['candidate']['connections'])==1
    assert client.get('/solutions/'+solution['id']).json()==solution
    confirmed=ask(journey,lambda c:reply(c),text='Confirm exactly this pending design').json()
    assert confirmed['pending']==first['pending']
    revised=ask(journey,lambda c:reply(c,[parameter(by_service(c,'dutch-ConfigureAndSynthesize')['target_ref'],3)])).json()
    assert revised['pending']['supersedes']==first['pending']['id']
    assert [s['node_id'] for s in steps(revised)]==first_ids
    replaced=ask(journey,lambda c:reply(c,[dict(kind='replace_service',node_id=by_service(c,'dutch-RunBenchmark')['target_ref'],value='{"service_id":"portugal-ActualC"}')])).json()
    assert [s['node_id'] for s in steps(replaced)]==first_ids
    assert steps(replaced)[0]['effective_settings']=={'count':3}
    assert steps(replaced)[1]['service_id']=='portugal-ActualC'
    # A further addition exercises cumulative batch replay with existing boundaries.
    expanded=ask(journey,lambda c:reply(c,[addition('dutch-RunBenchmark','second-view'),link(by_service(c,'dutch-ConfigureAndSynthesize')['target_ref'],'second-view')])).json()
    assert len(steps(expanded))==3 and len(expanded['pending']['candidate']['connections'])==2
    reopened=client.get(scope(solution)).json()
    explained=ask(journey,lambda c:reply(c),text='Explain before Apply').json()
    assert explained['pending']==reopened['pending']
    assert explained['pending']['candidate']['prior_assumptions']==first['pending']['candidate']['assumptions']
    assert explained['pending']['candidate']['assumptions']==[]
    assert client.get('/solutions/'+solution['id']).json()==solution
    assert apply(client,solution,first).status_code==409
    reviewed=explained['pending']['candidate']
    applied=apply(client,solution,explained); assert applied.status_code==200,applied.text
    current=client.get('/solutions/'+solution['id']).json()
    from app.services.solution_assistant import digest
    assert digest({k:current[k] for k in ('name','description','nodes','edges','design_metadata')})==reviewed['candidate_sha256']
    actual=[n for n in current['nodes'] if n.get('data',{}).get('service')]
    assert [(n['id'],n['data']['service']['id']) for n in actual]==[(s['node_id'],s['service_id']) for s in reviewed['steps']]
    assert actual[0]['data']['configuration']['parameters']=={'count':3}
    assert current['design_metadata']==solution['design_metadata']
    payload=workflow(current)
    for n in payload['nodes']:
        data=next(item['data'] for item in current['nodes'] if item['id']==n['node_id'])
        if data.get('configuration'):n['configuration']=data['configuration']
    compiled=client.post('/workflows/compile',json=payload); assert compiled.status_code==200,compiled.text
    assert compiled.json()['solution_studio_metadata']['capability_bindings']['status']=='verified'
    # Post-Apply edits must select the saved base and saved scoped reference.
    def saved_edit(c):
        assert c['pending_candidate'] is None
        step=next(s for s in c['saved_design']['steps'] if s['node_id']==first_ids[0])
        return reply(c,[parameter(step['target_ref'],4)],base='saved')
    post=ask(journey,saved_edit).json(); assert apply(client,solution,post).status_code==200
    now=client.get(scope(solution)).json()
    undone=client.post(scope(solution)+'/undo',json={k:now[k] for k in ('expected_updated_at','conversation_revision')})
    assert undone.status_code==200,undone.text
    restored=client.get('/solutions/'+solution['id']).json()
    assert restored['nodes']==current['nodes'] and restored['edges']==current['edges']
    # Undo for the initial cumulative Apply also restores its actual empty base.
    with SessionLocal() as db: assert db.query(ExecutionSubmission).count()==0


def test_two_copies_require_explicit_target_or_clarification(journey):
    first=create(journey)
    second=ask(journey,lambda c:reply(c,[addition('dutch-ConfigureAndSynthesize','another-source')])).json()
    copies=[s for s in steps(second) if s['service_id']=='dutch-ConfigureAndSynthesize']
    assert len(copies)==2 and copies[0]['target_ref']!=copies[1]['target_ref']
    clarified=ask(journey,lambda c:{**reply(c), 'outcome':'clarification','clarification':'Which displayed instance should change?'}).json()
    assert clarified['pending']==second['pending']
    chosen=copies[1]['node_id']
    changed=ask(journey,lambda c:reply(c,[parameter(next(s['target_ref'] for s in c['pending_candidate']['steps'] if s['node_id']==chosen),2)])).json()
    assert [s['effective_settings']['count'] for s in steps(changed) if s['service_id']=='dutch-ConfigureAndSynthesize']==[1,2]


@pytest.mark.parametrize('bad',['catalogue','raw-node','old-reference','other-proposal','bad-slot','wrong-revision','wrong-hash','cross-solution','non-string-reference'])
def test_ineligible_or_stale_references_preserve_review(journey,bad):
    client, solution, provider=journey
    original=create(journey); old_ref=steps(original)[0]['target_ref']
    current=ask(journey,lambda c:reply(c,[parameter(by_service(c,'dutch-ConfigureAndSynthesize')['target_ref'],2)])).json()
    other_ref=None
    if bad=='cross-solution':
        other=client.post('/solutions',json={'name':'Other review','nodes':[],'edges':[]}).json()
        other_ref=steps(create((client,other,provider)))[0]['target_ref']
    def invalid(c):
        ref=by_service(c,'dutch-ConfigureAndSynthesize')['target_ref']
        if bad=='catalogue':ref='dutch-ConfigureAndSynthesize'
        if bad=='raw-node':ref=steps(current)[0]['node_id']
        if bad=='old-reference':ref=old_ref
        if bad=='cross-solution':ref=other_ref
        value=reply(c,[parameter(ref,3)])
        if bad=='other-proposal': value['edit_base']['proposal_id']='a-different-proposal'
        if bad=='wrong-revision': value['edit_base']['conversation_revision']-=1
        if bad=='wrong-hash':value['edit_base']['candidate_sha256']='0'*64
        if bad=='bad-slot':value['solution_edits']=[dict(kind='disconnect',value=json.dumps({'source':ref,'target':c['pending_candidate']['steps'][1]['target_ref']})),dict(kind='connect',value=json.dumps({'source':ref,'target':c['pending_candidate']['steps'][1]['target_ref'],'source_slot':'invented','target_slot':'grid'}))]
        if bad=='non-string-reference':value['solution_edits']=[dict(kind='connect',value=json.dumps({'source':[], 'target':ref, 'source_slot':'grid','target_slot':'grid'}))]
        return value
    response=ask(journey,invalid)
    assert response.status_code in (409,422),response.text
    assert client.get(scope(solution)).json()==current
    assert client.get('/solutions/'+solution['id']).json()==solution


def test_stale_base_not_projected_and_undo_restores_empty_saved_graph(journey):
    client,solution,provider=journey
    proposal=create(journey)
    applied=apply(client,solution,proposal).json()
    undone=client.post(scope(solution)+'/undo',json={k:applied[k] for k in ('expected_updated_at','conversation_revision')})
    assert undone.status_code==200
    restored=client.get('/solutions/'+solution['id']).json()
    assert restored['nodes']==[] and restored['edges']==[] and restored['design_metadata']==solution['design_metadata']
    proposal=create(journey)
    client.put('/solutions/'+solution['id'],json={'name':'Concurrent Builder edit','expected_updated_at':restored['updated_at']})
    state=client.get(scope(solution)).json()
    assert not state['pending']['current'] and state['pending']['candidate'] is None
    assert apply(client,solution,state).status_code==409
    response=ask(journey,lambda c:reply(c))
    assert response.status_code==200 and provider.contexts[-1]['pending_candidate'] is None
    assert provider.contexts[-1]['edit_bases']['pending'] is None


def test_authority_drift_prevents_projection_before_model_dispatch(journey):
    client,solution,provider=journey
    proposal=create(journey)
    from app.models.service import Service
    with SessionLocal() as db:
        db.get(Service,'dutch-ConfigureAndSynthesize').image='changed-runtime:fixture'; db.commit()
    state=client.get(scope(solution)).json()
    assert state['pending']['current'] is False and state['pending']['candidate'] is None
    assert apply(client,solution,state).status_code==409
    ask(journey,lambda c:reply(c))
    assert provider.contexts[-1]['pending_candidate'] is None


def test_catalogue_change_during_reply_rejects_without_pending_mutation(journey):
    client,solution,provider=journey
    first=create(journey)
    def racing(c):
        from app.models.service import Service
        with SessionLocal() as db:
            db.get(Service,'dutch-RunBenchmark').image='changed-during-reply:fixture';db.commit()
        return reply(c,[parameter(by_service(c,'dutch-ConfigureAndSynthesize')['target_ref'],3)])
    result=ask(journey,racing)
    assert result.status_code==409 and 'authority changed' in result.text
    state=client.get(scope(solution)).json()
    assert state['conversation_revision']==first['conversation_revision'] and state['pending']['id']==first['pending']['id']
    assert client.get('/solutions/'+solution['id']).json()==solution
