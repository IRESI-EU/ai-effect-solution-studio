"""Offline fixtures for the explanation grounding fix; no real-provider retest."""
from copy import deepcopy

from app.models.design_ai import DesignDraft
from app.models.service import Service
from app.services import design_ai as service
from app.services import local_dutch_capture as capture
from app.schemas.design_ai import AssistantTurn
from test_guided_dutch import configure


def test_guided_facts_reach_provider_without_contract_or_execution_claim(environment, db, provider, monkeypatch):
    configure(monkeypatch)
    monkeypatch.setattr(capture,"enabled",lambda:True)
    db.get(Service,"dutch-ConfigureAndSynthesize").container_name="grid_synth_service"
    db.get(Service,"dutch-RunBenchmark").container_name="benchmark-runner"
    db.commit()
    draft = environment.post('/design-ai/drafts',json={'template_key':'dutch','guided':True}).json()
    before = deepcopy(db.get(DesignDraft,draft['id']).state)
    provider.turn = AssistantTurn(message="Offline explanation fixture",template_key=None,expected_revision=0,edits=[])
    response = environment.post('/design-ai/chat',json={'draft_id':draft['id'],'revision':0,'message':'Explain what this experiment does and what results I will receive.'})
    assert response.status_code==200
    facts=provider.contexts[-1]['guided_experiment']
    assert facts['optional_downloads']==list(capture.LABELS.values())
    assert [s['title'] for s in facts['steps']]==['Generate sample grid','Benchmark grid']
    assert 'Not inspected' in facts['execution_status']
    assert 'may be unavailable' in facts['availability']
    assert 'recorded benchmark values' in facts['expected_result_view']
    assert 'Missing operation contracts remain unresolved' in facts['limitations']
    db.expire_all()
    assert db.get(DesignDraft,draft['id']).state==before


def test_guided_facts_do_not_escape_local_approved_chain(environment, db, monkeypatch):
    configure(monkeypatch)
    draft = environment.post('/design-ai/drafts',json={'template_key':'dutch','guided':True}).json()
    row=db.get(DesignDraft,draft['id'])
    monkeypatch.setattr(capture,'enabled',lambda:False)
    assert service.guided_context(row) is None
    monkeypatch.setattr(capture,'enabled',lambda:True)
    # Fixture's other wrapper identities do not establish local capture support.
    assert service.guided_context(row) is None
    row.state={**row.state,'guided_experiment':None}
    assert service.guided_context(row) is None
