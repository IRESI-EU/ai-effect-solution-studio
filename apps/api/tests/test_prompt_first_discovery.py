"""Offline providers and isolated catalogue/database only; no SDK, ledger or execution."""
from copy import deepcopy
import json

from app.models.design_ai import DesignDraft
from app.models.service import Service
from app.schemas.design_ai import AssistantTurn
from app.services import local_dutch_capture as capture
from app.services.design_ai_provider import redact_context
from test_guided_dutch import configure


def approved_local(monkeypatch, db):
    configure(monkeypatch)
    monkeypatch.setattr(capture,'enabled',lambda:True)
    db.get(Service,'dutch-ConfigureAndSynthesize').container_name='grid_synth_service'
    db.get(Service,'dutch-RunBenchmark').container_name='benchmark-runner'
    db.commit()


def test_discovery_retrieves_approved_facts_without_creating_until_explicit_action(environment, db, provider, monkeypatch):
    approved_local(monkeypatch,db)
    provider.turn=AssistantTurn(message='Offline provider: Generate sample grid feeds Benchmark grid; expected results follow successful execution.',template_key='dutch',expected_revision=None,edits=[])
    response=environment.post('/design-ai/chat',json={'message':'Generate a sample electricity grid and benchmark it.'})
    assert response.status_code==200
    assert db.query(DesignDraft).count()==0
    value=response.json();assert value['draft'] is None
    context=provider.contexts[-1]
    assert [t['key'] for t in context['templates']]==['dutch']
    assert not context['discovery']['draft_exists']
    facts=context['guided_experiment']
    assert [step['title'] for step in facts['steps']]==['Generate sample grid','Benchmark grid']
    assert 'passed' in facts['connection']
    assert 'recorded benchmark values' in facts['expected_result_view']
    assert len(facts['optional_downloads'])==4
    assert 'No execution evidence' in facts['execution_status']
    assert value['recommendation']['key']=='dutch'
    assert value['recommendation']['optional_downloads']==facts['optional_downloads']
    serialized=json.dumps(redact_context(context))
    assert len(serialized)<16000
    assert all(text not in serialized for text in ('internal_host','internal_port','api_key','http://','file://'))
    assert len([a for a in value['activity'] if a['tool']!='tools/list'])<=6
    created=environment.post('/design-ai/drafts',json={'template_key':'dutch','guided':True}).json()
    assert created['design']['run_input']=={'seed':42}
    assert db.query(DesignDraft).count()==1
    # Discovery after a copy exists still neither selects nor changes it.
    state=deepcopy(db.get(DesignDraft,created['id']).state)
    again=environment.post('/design-ai/chat',json={'message':'Explain the supported experiment.'})
    assert again.status_code==200 and again.json()['draft'] is None
    db.expire_all();assert db.get(DesignDraft,created['id']).state==state


def test_unsupported_and_invalid_recommendations_cannot_invent_create_or_expand_scope(environment, db, provider, monkeypatch):
    approved_local(monkeypatch,db)
    provider.turn=AssistantTurn(message='Forecasting and uploaded datasets are not supported by the enabled local sample-grid experiment.',template_key=None,expected_revision=None,edits=[])
    response=environment.post('/design-ai/chat',json={'message':'Upload my dataset and forecast tomorrow.'})
    assert response.status_code==200 and response.json()['recommendation'] is None
    provider.turn=provider.turn.model_copy(update={'template_key':'denmark'})
    assert environment.post('/design-ai/chat',json={'message':'An unsupported experiment'}).status_code==422
    db.get(Service,'dutch-RunBenchmark').status='rejected';db.commit()
    provider.turn=provider.turn.model_copy(update={'template_key':'dutch'})
    assert environment.post('/design-ai/chat',json={'message':'Generate a grid'}).status_code==422
    assert not provider.contexts[-1]['templates']
    assert 'guided_experiment' not in provider.contexts[-1]
    assert db.query(DesignDraft).count()==0
