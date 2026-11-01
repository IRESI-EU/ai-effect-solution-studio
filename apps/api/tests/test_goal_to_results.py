"""OFFLINE integration: explicit provider/runtime/algorithm doubles, not live acceptance."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from fastapi import HTTPException
import app.main as main
from app.core.config import settings
from app.db import SessionLocal
from app.models.design_ai import DesignDraft
from app.models.deployment import Deployment
from app.models.execution_submission import ExecutionSubmission
from app.models.operation_contract import OperationContract
from app.models.service import Service
from app.models.solution import Solution
from app.models.user import User
from app.models.local_dutch_execution import LocalDutchExecution
from app.routers import deployment_results
from app.routers.design_ai import pilot_user
from app.schemas.design_ai import AssistantTurn
from app.services import capability_readiness, orchestrator_adapter, qualified_demo
from app.services.dutch_capture_contract import BASE_IMAGES, NODE_KEYS, SOURCE_REVISION, VERSION, task_id
from app.services.dutch_capture_contract import CaptureStore, encode, safe_benchmark, sha

WF = 'wf-112233445566'
GOAL = 'Create a sample electricity grid using seed 43 and benchmark it.'


@pytest.fixture
def qualified(environment, db, provider, monkeypatch, tmp_path):
    definitions = json.loads((Path(__file__).resolve().parents[3] / 'deploy/aie37/contracts.json').read_text())
    source = db.get(Solution, 'source-dutch')
    nodes = deepcopy(source.nodes)
    for node in nodes:
        data = node.get('data', {})
        if not data.get('service'):
            continue
        sid = data['service']['id']
        service = db.get(Service, sid)
        operation = service.operation_name
        role = 'synth' if operation == 'ConfigureAndSynthesize' else 'benchmark'
        service.container_name = 'grid_synth_service' if role == 'synth' else 'benchmark-runner'
        service.internal_host = f'seed-{role}'
        definition = definitions[operation]
        contract = OperationContract(id=f'qualified-{role}', service_id=sid, status='active', **definition)
        db.add(contract)
        data['operation_contract'] = {'contract_id': contract.id, 'contract_version': '1.0.0'}
        if role == 'synth':
            data['configuration'] = {**data['operation_contract'], 'parameters': {'seed': 42}}
    ids = {n['id'] for n in nodes if n.get('data', {}).get('service')}
    edges = deepcopy(source.edges)
    for edge in edges:
        if edge['source'] in ids and edge['target'] in ids:
            edge['data'] = {'binding': {'source_slot': 'captured_grid', 'target_slot': 'captured_grid'}}
    source.nodes, source.edges = nodes, edges
    db.commit()
    for key, value in {'design_ai_templates': json.dumps({'dutch': {'solution_id': source.id,
        'instance_settings_only': True, 'qualified_experiment': True}}),
        'design_ai_dutch_demo': True, 'aie37_qualification': True,
        'database_url': 'postgresql://test@postgres/design_aie37_qualification',
        'orchestrator_base_url': 'http://seed-orchestrator:8000',
        'local_dutch_auto_capture_root': str(tmp_path / 'capture'),
        'local_dutch_capture_runtime': str(tmp_path / 'runtime.json'),
        'design_ai_demo_execution_grant_file': ''}.items():
        monkeypatch.setattr(settings, key, value)
    pins = {'version': VERSION, 'source_revision': SOURCE_REVISION, 'adapter_sha256': 'a'*64, 'contract_sha256': 'b'*64,
        'images': {role: {'id': 'sha256:'+'c'*64, 'base_image': digest} for role, digest in BASE_IMAGES.items()}}
    (tmp_path / 'runtime.json').write_text(json.dumps(pins))
    monkeypatch.setattr(main, 'run_runtime_preflight', lambda *_: {'status': 'ready', 'results': []})
    monkeypatch.setattr(main, 'require_binding_transport', lambda *_: {'status': 'ready'})
    monkeypatch.setattr(capability_readiness, 'require_binding_transport', lambda *_: {'status': 'ready'})
    monkeypatch.setattr(orchestrator_adapter, 'require_parameter_transport', lambda *_: {'status': 'ready'})
    calls = []
    def submit(payload):
        with SessionLocal() as session:
            assert session.query(ExecutionSubmission).filter(ExecutionSubmission.phase == 'dispatching').count() == 1
        calls.append(deepcopy(payload))
        return {'workflow_id': WF, 'status': 'running'}
    monkeypatch.setattr(main, 'submit_to_orchestrator', submit)
    provider.turn = AssistantTurn(message='OFFLINE provider double: recommend the existing registered Dutch workflow with seed 43. Results require successful execution and capture.',
        template_key='dutch', expected_revision=None, edits=[], recommended_seed=43)
    workflow = {'workflow_id': WF, 'status': 'completed'}
    tasks = [{'task_id': task_id(role), 'node_key': key, 'status': 'completed'} for role, key in NODE_KEYS.items()]
    monkeypatch.setattr(deployment_results, 'get_workflow_status', lambda _: deepcopy(workflow))
    monkeypatch.setattr(deployment_results, 'get_workflow_tasks', lambda _: {'tasks': deepcopy(tasks)})
    return {'client': environment, 'provider': provider, 'calls': calls, 'db': db, 'path': tmp_path, 'workflow': workflow, 'pins': pins, 'tasks': tasks}


def create_copy(q):
    client = q['client']
    count = q['db'].query(DesignDraft).count()
    templates = client.get('/design-ai/templates').json()
    item = next(item for item in templates if item['key'] == 'dutch')
    assert item.get('guided_available'), item.get('reason')
    response = client.post('/design-ai/chat', json={'message': GOAL})
    assert response.status_code == 200, response.text
    recommendation = response.json()['recommendation']
    assert q['db'].query(DesignDraft).count() == count
    assert recommendation['mechanism'] == 'registered_workflow' and recommendation['recommended_seed'] == 43
    assert 'arbitrary' in recommendation['scope']
    response = client.post('/design-ai/drafts', json={'template_key': 'dutch', 'guided': True,
        'recommended_seed': recommendation['recommended_seed'], 'recommendation_revision': recommendation['source_revision']})
    assert response.status_code == 200, response.text
    return response.json()


def saved_copy(q):
    draft = create_copy(q)
    base = f"/design-ai/drafts/{draft['id']}"
    assert draft['revision'] == 0 and draft['pending'] and draft['design']['run_input'] is None
    applied = q['client'].post(base+'/apply', json={'revision': 0, 'proposal_id': draft['pending']['id']})
    assert applied.status_code == 200, applied.text
    saved = q['client'].post(base+'/save', json={'revision': 1})
    assert saved.status_code == 200, saved.text
    return base, saved.json()['draft']


def grant(q):
    value = {'id': 'OFFLINE-TEST-GRANT', 'profile': 'qualified-dutch-goal-to-results', 'owner_id': 'designer',
        'seed': 43, 'source_solution_id': 'source-dutch', 'max_attempts': 1,
        'approved_by': 'explicit automated test double', 'approved_at': '2026-10-31T00:00:00+00:00'}
    path = q['path'] / 'OFFLINE-test-grant.json'
    path.write_text(json.dumps(value))
    return str(path)


def prepared(q, monkeypatch, authorize=True):
    base, draft = saved_copy(q)
    if authorize:
        monkeypatch.setattr(settings, 'design_ai_demo_execution_grant_file', grant(q))
    response = q['client'].post(base+'/execution-review', json={'revision': 1})
    assert response.status_code == 200, response.text
    return base, draft, response.json()


def execute(q, base, review):
    return q['client'].post(base+'/execute', json={'revision': 1, 'submission_id': review['attempt']['submission_id'], 'confirm_execution': True})


def test_goal_copy_apply_full_undo_save_and_no_implicit_execution(qualified):
    q = qualified
    draft = create_copy(q); base=f"/design-ai/drafts/{draft['id']}"
    before=deepcopy(draft['design'])
    assert q['client'].post(base+'/save',json={'revision':0}).status_code==409
    applied=q['client'].post(base+'/apply',json={'revision':0,'proposal_id':draft['pending']['id']}).json()
    seed=next(n['data']['configuration']['parameters']['seed'] for n in applied['design']['nodes'] if n.get('data',{}).get('configuration'))
    assert seed==43
    undone=q['client'].post(base+'/undo',json={'revision':1}).json()
    assert undone['design']==before and undone['revision']==2
    pending=q['client'].post(base+'/guided-settings',json={'revision':2,'seed':43}).json()
    q['client'].post(base+'/apply',json={'revision':2,'proposal_id':pending['pending']['id']})
    saved=q['client'].post(base+'/save',json={'revision':3}).json()['draft']
    assert saved['saved_solution_id'] and not saved['dirty']
    assert len(q['provider'].contexts)==1 and not q['calls']
    assert q['db'].query(Deployment).count()==q['db'].query(ExecutionSubmission).count()==0


def test_explicit_confirmation_registers_durably_and_replay_dispatches_once(qualified,monkeypatch):
    q=qualified; base,draft,review=prepared(q,monkeypatch)
    assert review['execution_authorized'] and not q['calls']
    assert q['client'].post(base+'/execute',json={'revision':1,'submission_id':review['attempt']['submission_id'],'confirm_execution':False}).status_code==422
    response=execute(q,base,review)
    assert response.status_code==200,response.text
    assert response.json()['attempt']['workflow_id']==WF
    assert q['client'].get('/deployments/by-workflow/'+WF).status_code==200
    assert execute(q,base,review).status_code==200 and len(q['calls'])==1
    assert q['client'].get(base+'/execution').json()['attempt']['workflow_id']==WF
    assert q['client'].get('/workflows/'+WF+'/submitted-configuration').json()['submitted']['request']['nodes'][0]['configuration']['parameters']['seed']==43
    assert q['db'].query(Deployment).count()==1


def test_missing_authorization_cannot_dispatch_or_bypass_through_legacy_route(qualified,monkeypatch):
    q=qualified; base,draft,review=prepared(q,monkeypatch,False)
    assert not review['execution_authorized']
    assert execute(q,base,review).status_code==403 and not q['calls']
    assert q['client'].post('/workflows/submit-to-orchestrator',json={'name':'bypass','nodes':[],'edges':[]}).status_code==403


@pytest.mark.parametrize('failure',['timeout','missing_identity','historical_identity'])
def test_uncertainty_is_durable_not_retryable_or_replaced_by_history(qualified,monkeypatch,failure):
    q=qualified; base,draft,review=prepared(q,monkeypatch)
    def submit(_):
        q['calls'].append('test double')
        if failure=='timeout': raise HTTPException(502,'OFFLINE simulated transport timeout; acceptance unknown')
        return {} if failure=='missing_identity' else {'workflow_id':WF,'status':'running'}
    if failure=='historical_identity':
        q['db'].add(Deployment(id='old',workflow_id=WF,name='preserved old run',created_by_user_id='designer'));q['db'].commit()
    monkeypatch.setattr(main,'submit_to_orchestrator',submit)
    assert execute(q,base,review).status_code in (409,502)
    attempt=q['client'].get(base+'/execution').json()['attempt']
    assert attempt['phase']=='submission_unknown' and attempt['workflow_id'] is None
    assert execute(q,base,review).status_code==409 and len(q['calls'])==1


def test_stale_proposal_save_and_execution_cannot_mutate_or_dispatch(qualified,monkeypatch):
    q=qualified; base,draft,review=prepared(q,monkeypatch)
    assert q['client'].post(base+'/save',json={'revision':0}).status_code==409
    saved=q['db'].get(Solution,draft['saved_solution_id']);saved.name='Changed in another view';q['db'].commit()
    assert execute(q,base,review).status_code==409 and not q['calls']
    assert q['client'].post(base+'/execution-review',json={'revision':1}).status_code==409


def test_unavailable_or_incompatible_catalogue_has_no_recommendation_or_copy(qualified):
    q=qualified; service=q['db'].get(Service,'dutch-RunBenchmark');service.status='rejected';q['db'].commit()
    assert q['client'].post('/design-ai/chat',json={'message':GOAL}).status_code==422
    assert q['db'].query(DesignDraft).count()==0
    assert not q['provider'].contexts[-1].get('guided_experiment')


def test_unsupported_goal_refusal_is_draft_free(qualified):
    q=qualified;q['provider'].turn=AssistantTurn(message='OFFLINE double: forecasting is unsupported',template_key=None,expected_revision=None,edits=[])
    result=q['client'].post('/design-ai/chat',json={'message':'Forecast tomorrow from uploaded telemetry'})
    assert result.status_code==200 and result.json()['recommendation'] is None
    assert q['db'].query(DesignDraft).count()==0


def test_catalogue_or_contract_change_invalidates_pre_creation_review(qualified):
    q=qualified
    recommendation=q['client'].post('/design-ai/chat',json={'message':GOAL}).json()['recommendation']
    contract=q['db'].get(OperationContract,'qualified-synth')
    definition=deepcopy(contract.definition);definition['compatibility_notes'].append('OFFLINE changed after recommendation')
    contract.definition=definition;q['db'].commit()
    response=q['client'].post('/design-ai/drafts',json={'template_key':'dutch','guided':True,'recommended_seed':43,
        'recommendation_revision':recommendation['source_revision']})
    assert response.status_code==409 and q['db'].query(DesignDraft).count()==0 and not q['calls']


def test_other_owner_cannot_access_attempt_or_results(qualified,monkeypatch):
    q=qualified;base,draft,review=prepared(q,monkeypatch);assert execute(q,base,review).status_code==200
    main.app.dependency_overrides[pilot_user]=lambda:q['db'].get(User,'other')
    try:
        assert q['client'].get(base+'/execution').status_code==404
        assert execute(q,base,review).status_code==404
    finally:main.app.dependency_overrides.pop(pilot_user)
    q['client'].post('/auth/logout')
    assert q['client'].get('/deployments/by-workflow/'+WF+'/results').status_code==401


@pytest.mark.parametrize("terminal_status", ["completed", "failed"])
def test_failed_execution_and_unavailable_capture_are_not_success_results(qualified, monkeypatch, terminal_status):
    q=qualified
    # Distinct terminal histories: never rewrite a recorded completed observation
    # into a different failed history to construct the next test case.
    q['workflow']['status']=terminal_status
    if terminal_status=='failed':q['tasks'][1]['status']='failed'
    base,draft,review=prepared(q,monkeypatch);assert execute(q,base,review).status_code==200
    result=q['client'].get('/deployments/by-workflow/'+WF+'/results').json()
    assert result['workflow']['status']==terminal_status and result['evidence']['state']!='available'
    assert len(q['calls'])==1


def test_exact_new_run_capture_downloads_and_later_edits_keep_historical_seed(qualified,monkeypatch):
    q=qualified;base,draft,review=prepared(q,monkeypatch);assert execute(q,base,review).status_code==200
    snapshot=q['db'].query(LocalDutchExecution).one().submitted
    root=q['path']/'capture'
    def provenance(role):
        return {'version':VERSION,'source_revision':SOURCE_REVISION,'base_image':BASE_IMAGES[role],
            'adapter_sha256':q['pins']['adapter_sha256'],'contract_sha256':q['pins']['contract_sha256']}
    request={'workflow_id':WF,'task_id':task_id('synth'),'method':'ConfigureAndSynthesize','inputs':[],
        'configuration':snapshot['task_configurations'][NODE_KEYS['synth']]}
    graph=b'{"OFFLINE algorithm double":true}'
    grid={'grid_data':{'grid_id':'OFFLINE-test-grid','seed':43,'source_config':{'seed':43},
        'metadata':{'nodes':'3','edges':'2'},'pandapower_json':graph.decode()}}
    reference=CaptureStore(root/'synth','synth',provenance('synth')).execute(request,
        lambda:({'configuration':encode({'config':{'seed':43},'algorithm_consumed':{'seed':43}}),'grid':encode(grid),'network':graph},None))
    manifest=(root/'synth'/WF/task_id('synth')/'manifest.json').read_bytes()
    upstream={'workflow_id':WF,'task_id':task_id('synth'),'manifest_sha256':sha(manifest),
        'grid_sha256':json.loads(manifest)['files']['grid']['sha256']}
    raw=encode({'kpis':{'carbon_intensity':[655]},'episodes':[{'episode_index':0,'steps':11,'runtime_seconds':.2,'overload_violations':0,'terminated':True}],
        'metadata':{'scenario_count':1,'upstream_grid_id':'OFFLINE-test-grid','upstream_grid_nodes':3,'upstream_grid_edges':2,'upstream_grid_adapter':'benchmark-service'}})
    benchmark_ref=CaptureStore(root/'benchmark','benchmark',provenance('benchmark')).execute(
        {'workflow_id':WF,'task_id':task_id('benchmark'),'method':'RunBenchmark','inputs':[reference]},
        lambda:({'benchmark_source':raw,'benchmark':encode(safe_benchmark(raw,upstream))},upstream))
    q['tasks'][0].update(input_refs=[],output_refs=[reference])
    q['tasks'][1].update(input_refs=[reference],output_refs=[benchmark_ref])
    url='/deployments/by-workflow/'+WF+'/results'
    response=q['client'].get(url);assert response.status_code==200,response.text
    evidence=response.json()['evidence'];assert evidence['state']=='available',evidence.get('message')
    assert evidence['executed_seed']==43 and evidence['grid']['nodes']==3
    assert len(evidence['artifacts'])==4 and evidence['benchmark']
    for artifact in evidence['artifacts']:
        response=q['client'].get(artifact['download_url'].removeprefix('/api'))
        assert response.status_code==200 and sha(response.content)==artifact['sha256']
    pending=q['client'].post(base+'/guided-settings',json={'revision':1,'seed':42}).json()
    assert q['client'].post(base+'/apply',json={'revision':1,'proposal_id':pending['pending']['id']}).status_code==200
    assert q['client'].post(base+'/save',json={'revision':2}).status_code==200
    assert q['client'].get(url).json()['evidence']==evidence and len(q['calls'])==1
    def unavailable(_):raise HTTPException(503,'OFFLINE unavailable runtime double')
    monkeypatch.setattr(deployment_results,'get_workflow_status',unavailable)
    recorded=q['client'].get(url).json()
    assert recorded['workflow']['status']=='completed' and recorded['evidence']==evidence
    assert recorded['status_source']=='recorded terminal observation for this run'
    assert [task['status'] for task in recorded['tasks']]==['completed','completed']
    for artifact in evidence['artifacts']:
        assert q['client'].get(artifact['download_url'].removeprefix('/api')).status_code==200


def test_second_saved_copy_cannot_spend_the_same_execution_grant(qualified,monkeypatch):
    q=qualified;base,draft,review=prepared(q,monkeypatch);assert execute(q,base,review).status_code==200
    # Each creation is explicit; the permission belongs to one attempt globally.
    other_base,other_draft,other_review=prepared(q,monkeypatch)
    assert execute(q,other_base,other_review).status_code==409 and len(q['calls'])==1


def test_real_provider_boundary_is_stopped_before_sdk_by_exhausted_allowance(qualified,monkeypatch):
    from app.services import design_ai_budget,design_ai_provider
    q=qualified
    class Exhausted:
        def __init__(self,*a,**kw):pass
        def reserve(self,*a,**kw):raise HTTPException(429,'OFFLINE exhausted allowance double')
    monkeypatch.setattr(design_ai_budget,'Budget',Exhausted)
    monkeypatch.setattr(settings,'openai_api_key','OFFLINE-UNUSABLE-TEST-KEY')
    monkeypatch.setattr(settings,'design_ai_model','gpt-6-luna')
    monkeypatch.setattr(settings,'design_ai_reasoning_effort','low')
    monkeypatch.setattr(settings,'design_ai_max_output_tokens',2000)
    monkeypatch.setattr(settings,'design_ai_acceptance_budget_file','OFFLINE-test-ledger')
    monkeypatch.setattr(settings,'design_ai_acceptance_task_limit_file','OFFLINE-scoped-checkpoint')
    monkeypatch.setattr(design_ai_provider,'AsyncOpenAI',lambda **kw:pytest.fail('SDK must not be reached'))
    main.app.dependency_overrides[design_ai_provider.get_provider]=lambda:design_ai_provider.OpenAIProvider()
    assert q['client'].post('/design-ai/chat',json={'message':GOAL}).status_code==429
    assert q['db'].query(DesignDraft).count()==0 and not q['calls']


def test_offline_review_cannot_use_the_new_execution_route(qualified,monkeypatch):
    q=qualified;base,draft,review=prepared(q,monkeypatch)
    monkeypatch.setattr(settings,'design_ai_dutch_demo',False)
    assert execute(q,base,review).status_code==403 and not q['calls']


@pytest.mark.parametrize('missing',['ledger','checkpoint'])
def test_demo_provider_needs_both_ledger_and_checkpoint_before_sdk(qualified,monkeypatch,missing):
    from app.services import design_ai_provider
    q=qualified
    monkeypatch.setattr(settings,'openai_api_key','OFFLINE-UNUSABLE-TEST-KEY')
    monkeypatch.setattr(settings,'design_ai_model','gpt-6-luna')
    monkeypatch.setattr(settings,'design_ai_acceptance_budget_file','' if missing=='ledger' else 'OFFLINE-ledger')
    monkeypatch.setattr(settings,'design_ai_acceptance_task_limit_file','' if missing=='checkpoint' else 'OFFLINE-checkpoint')
    monkeypatch.setattr(design_ai_provider,'AsyncOpenAI',lambda **kw:pytest.fail('SDK must not be reached'))
    main.app.dependency_overrides[design_ai_provider.get_provider]=lambda:design_ai_provider.OpenAIProvider()
    assert q['client'].post('/design-ai/chat',json={'message':GOAL}).status_code==503
    assert q['db'].query(DesignDraft).count()==0 and not q['calls']
