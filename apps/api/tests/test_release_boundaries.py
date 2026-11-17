"""Prepared configuration boundaries; no Docker or external provider calls."""
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[3]


def test_production_overlay_is_default_off_and_keeps_experimental_execution_disconnected():
    document=yaml.safe_load((ROOT/'deploy/release/restricted-beta.compose.yaml').read_text())
    assert set(document['services'])=={'api','web'}
    env=document['services']['api']['environment']
    assert env['DESIGN_AI_ENABLED']=='${BETA_ENABLED:-false}'
    assert env['DESIGN_AI_RESTRICTED_BETA']=='true'
    assert env['OPENAI_API_KEY']==env['DESIGN_AI_BUDGET_AUTHORITY_TOKEN']==''
    assert env['PORTUGUESE_SUPERVISED_MODE']=='false'
    assert env['DESIGN_AI_DEMO_EXECUTION_GRANT_FILE']==''
    assert 'networks' not in document and 'ports' not in document['services']['api']
    assert 'postgres' not in document['services'] and 'worker' not in document['services']


def test_only_staging_https_gateway_gets_publishable_edge_network():
    base=yaml.safe_load((ROOT/'deploy/staging/compose.yaml').read_text())
    overlay=yaml.safe_load((ROOT/'deploy/release/staging-design-only.compose.yaml').read_text())
    assert overlay['services']['gateway']['networks']==['private','review_edge']
    assert overlay['networks']['review_edge']['internal'] is False
    for name in ('api','web','postgres'):
        assert base['services'][name]['networks']==['private']
        assert 'networks' not in overlay['services'].get(name,{})
        assert not base['services'][name].get('ports')
    assert base['services']['gateway']['ports'][0].startswith('127.0.0.1:')


def test_staging_adaptation_allows_chat_route_without_relaxing_denial_or_tls():
    base=yaml.safe_load((ROOT/'deploy/staging/compose.yaml').read_text())
    assert base['networks']['private']['internal'] is True
    assert base['services']['gateway']['ports'][0].startswith('127.0.0.1:')
    assert base['services']['api']['environment']['SECURE_COOKIES']=='true'
    nginx=(ROOT/'deploy/release/staging-design-only.nginx.conf').read_text()
    assert 'location ~ ^/api/design-ai/chat' not in nginx
    for route in ('submit-to-orchestrator','workflows/submit/','runtime-preflight','/execute/','runtime/verify','data-references/preview'):
        assert route in nginx
    assert 'ssl_protocols TLSv1.2 TLSv1.3' in nginx
    env=yaml.safe_load((ROOT/'deploy/release/staging-design-only.compose.yaml').read_text())['services']['api']['environment']
    assert env['OPENAI_API_KEY']==env['DESIGN_AI_BUDGET_AUTHORITY_TOKEN']==''
