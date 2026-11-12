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


@pytest.mark.parametrize("failure",["not_restricted","several_reviewers","wrong_profile","missing_authority"])
def test_local_pilot_requires_one_reviewer_qualified_profile_and_shared_accounting(environment,monkeypatch,provider,failure):
    from app.services import qualified_demo
    monkeypatch.setattr(settings,"design_ai_local_pilot",True)
    monkeypatch.setattr(settings,"design_ai_restricted_beta",failure!="not_restricted")
    monkeypatch.setattr(settings,"design_ai_reviewer_ids","designer,other" if failure=="several_reviewers" else "designer")
    monkeypatch.setattr(qualified_demo,"profile_enabled",lambda:failure!="wrong_profile")
    monkeypatch.setattr(settings,"design_ai_budget_authority_url","" if failure=="missing_authority" else "http://127.0.0.1:1")
    assert environment.get("/design-ai/config").status_code==503
    assert environment.post("/design-ai/chat",json={"message":"Never send"}).status_code==503
    assert provider.contexts==[]


def test_local_pilot_notice_and_single_reviewer_guard_do_not_enable_accounting_or_provider(environment,monkeypatch,provider):
    from app.services import qualified_demo
    monkeypatch.setattr(settings,"design_ai_local_pilot",True)
    monkeypatch.setattr(settings,"design_ai_restricted_beta",True)
    monkeypatch.setattr(settings,"design_ai_reviewer_ids","designer")
    monkeypatch.setattr(qualified_demo,"profile_enabled",lambda:True)
    # Incomplete authority config must fail closed without attempting a connection.
    monkeypatch.setattr(settings,"design_ai_budget_authority_url","http://127.0.0.1:1")
    value=environment.get("/design-ai/config").json()
    assert value["pilot_notice"].startswith("Restricted local design-only pilot")
    assert value["provider_configured"] is False
    assert value["test_allowance"]["blocked_reason"]=="accounting_unavailable"
    monkeypatch.setattr(settings,"design_ai_reviewer_ids","other")
    assert environment.get("/design-ai/config").status_code==403
    assert environment.post("/design-ai/chat",json={"message":"Never send"}).status_code==403
    assert provider.contexts==[]


@pytest.mark.parametrize("ledger,task", [("",""),("unopened-ledger",""),("","unopened-checkpoint")])
def test_beta_cannot_fall_back_to_unbudgeted_provider_calls(environment, monkeypatch, ledger, task):
    import asyncio
    from fastapi import HTTPException
    from app.services import design_ai_provider as provider
    monkeypatch.setattr(settings,"design_ai_restricted_beta",True)
    monkeypatch.setattr(settings,"design_ai_reviewer_ids","designer")
    monkeypatch.setattr(settings,"openai_api_key","test-only-never-sent")
    monkeypatch.setattr(settings,"design_ai_model","gpt-6-luna")
    monkeypatch.setattr(settings,"design_ai_acceptance_budget_file",ledger)
    monkeypatch.setattr(settings,"design_ai_acceptance_task_limit_file",task)
    monkeypatch.setattr(provider,"AsyncOpenAI",lambda **kw: pytest.fail("SDK must never be constructed"))
    assert not provider.configured()
    with pytest.raises(HTTPException,match="durable shared accounting"):
        asyncio.run(provider.OpenAIProvider().respond({"request":"Never send"}))
    assert environment.get("/design-ai/config").json()["provider_configured"] is False
