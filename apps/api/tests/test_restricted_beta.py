"""Backend restrictions use existing account IDs, independently of the UI."""
import pytest

from app.core.config import settings
from app.models.user import User


def test_beta_denies_unnamed_active_users_on_all_design_routes(environment, monkeypatch, provider):
    monkeypatch.setattr(settings, "design_ai_restricted_beta", True)
    monkeypatch.setattr(settings, "design_ai_reviewer_ids", "other")
    for path in ("config", "templates", "drafts", "drafts/missing"):
        assert environment.get("/design-ai/" + path).status_code == 403
    for path, body in (("drafts", {"template_key":"dutch"}), ("chat", {"message":"Never send"}),
                       ("drafts/missing/apply", {"revision":0,"proposal_id":"missing"}),
                       ("drafts/missing/undo", {"revision":0}), ("drafts/missing/save", {"revision":0})):
        assert environment.post("/design-ai/" + path, json=body).status_code == 403
    assert provider.contexts == []


@pytest.mark.parametrize("ids", ["", "designer@example.test", "Designer", "other, designer-extra"])
def test_beta_allowlist_fails_closed_and_does_not_match_emails_or_prefixes(environment, monkeypatch, ids):
    monkeypatch.setattr(settings, "design_ai_restricted_beta", True)
    monkeypatch.setattr(settings, "design_ai_reviewer_ids", ids)
    assert environment.get("/design-ai/config").status_code == 403


def test_named_reviewer_can_use_existing_controls_but_logout_denies_config(environment, monkeypatch):
    monkeypatch.setattr(settings, "design_ai_restricted_beta", True)
    monkeypatch.setattr(settings, "design_ai_reviewer_ids", " other, designer ")
    assert environment.get("/design-ai/config").status_code == 200
    assert environment.get("/design-ai/drafts").status_code == 200
    environment.post("/auth/logout")
    assert environment.get("/design-ai/config").status_code == 403


def test_platform_admin_has_no_beta_bypass(environment, db, monkeypatch):
    user = db.get(User, "designer")
    user.role = "platform_admin"
    db.commit()
    monkeypatch.setattr(settings, "design_ai_restricted_beta", True)
    monkeypatch.setattr(settings, "design_ai_reviewer_ids", "other")
    assert environment.get("/design-ai/config").status_code == 403
    assert environment.get("/design-ai/drafts").status_code == 403


def test_beta_flag_defaults_preserve_existing_disabled_mode_config(environment):
    assert not settings.design_ai_restricted_beta
    environment.post("/auth/logout")
    assert environment.get("/design-ai/config").status_code == 200
