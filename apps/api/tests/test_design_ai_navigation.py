"""Focused read-only draft-selection checks using isolated database fixtures."""
from copy import deepcopy

from app.main import app
from app.models.design_ai import DesignDraft
from app.models.user import User
from app.routers.design_ai import pilot_user
from app.services import design_ai as service


def test_start_screen_lists_without_creating_or_mutating_drafts(environment, db):
    assert environment.get('/design-ai/drafts').json() == []
    assert db.query(DesignDraft).count() == 0
    first = environment.post('/design-ai/drafts', json={'template_key': 'dutch'}).json()
    second = environment.post('/design-ai/drafts', json={'template_key': 'dutch'}).json()
    assert first['id'] != second['id']
    other = service.start('dutch', db, db.get(User, 'other'))
    before = {r.id: (r.revision, deepcopy(r.state), r.updated_at) for r in db.query(DesignDraft).all()}
    response = environment.get('/design-ai/drafts')
    assert response.status_code == 200
    choices = response.json()
    assert {r['id'] for r in choices} == {first['id'], second['id']}
    assert all(r['name'] and 'updated_at' in r and 'revision' in r for r in choices)
    assert all('state' not in r and 'owner_id' not in r for r in choices)
    assert environment.get('/design-ai/drafts/' + first['id']).json() == first
    assert environment.get('/design-ai/drafts/' + other['id']).status_code == 404
    assert environment.get('/design-ai/drafts/missing').status_code == 404
    db.expire_all()
    assert {r.id: (r.revision, r.state, r.updated_at) for r in db.query(DesignDraft).all()} == before
    app.dependency_overrides[pilot_user] = lambda: db.get(User, 'other')
    try:
        assert {r['id'] for r in environment.get('/design-ai/drafts').json()} == {other['id']}
    finally:
        app.dependency_overrides.pop(pilot_user)
    environment.post('/auth/logout')
    assert environment.get('/design-ai/drafts').status_code == 401
