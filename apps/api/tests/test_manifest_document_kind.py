"""Regression for pasting a standalone OpenAPI into the manifest import field."""
from copy import deepcopy
import json
from pathlib import Path

from app.db import SessionLocal
from app.models.service import Service
from app.services.service_manifest_importer import preview_service_manifest
from test_parameter_onboarding import publisher, manifest  # noqa: F401

DOCUMENT = json.loads((Path(__file__).resolve().parents[3] / 'docs/parameter-onboarding/portugal-source-openapi.json').read_text())


def test_pasted_openapi_reports_one_actionable_error_without_registering(publisher):
    client = publisher
    with SessionLocal() as db: before = db.query(Service).count()
    response = client.post('/services/import/preview-manual', json={'manifest': DOCUMENT})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['status'] == 'invalid' and result['service'] is None
    assert result['raw_manifest'] == DOCUMENT
    assert len(result['validation']) == 1
    message = result['validation'][0]['message']
    assert 'OpenAPI interface description' in message and 'not an AI-EFFECT service manifest' in message
    assert 'Adjustable service settings' in message and 'does not publish or enable' in message
    assert client.post('/services/import/confirm-manual', json={'manifest': DOCUMENT}).status_code == 400
    with SessionLocal() as db: assert db.query(Service).count() == before


def test_git_openapi_reports_same_error_and_nested_manifest_still_works(publisher, monkeypatch):
    monkeypatch.setattr('app.services.service_manifest_importer.fetch_json', lambda *a: deepcopy(DOCUMENT))
    preview = preview_service_manifest('https://github.com/Example/Repository')
    assert preview.status == 'invalid' and preview.service is None
    assert len([v for v in preview.validation if v.level == 'error']) == 1
    complete = manifest('full-manifest-document-kind')
    complete['interface'].pop('parameter_schema')
    complete['interface'].update(openapi=DOCUMENT, openapi_operation_id=DOCUMENT['paths']['/train']['post']['operationId'])
    response = publisher.post('/services/import/preview-manual', json={'manifest': complete})
    assert response.status_code == 200 and response.json()['status'] != 'invalid', response.text
    response = publisher.post('/services/import/confirm-manual', json={'manifest': complete})
    assert response.status_code == 200, response.text
    saved = publisher.get('/services/full-manifest-document-kind/parameter-onboarding').json()
    assert {c['name'] for c in saved['discovery']['candidates'] if c['supported']} == {'sequence_len', 'epochs', 'batch_size'}
