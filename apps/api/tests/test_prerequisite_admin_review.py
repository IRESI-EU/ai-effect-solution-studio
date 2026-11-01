"""Isolated review regressions; no demo accounts, runtime or provider access."""
from copy import deepcopy
import pytest

from app.db import SessionLocal
from app.models.user import AuditEvent, User


def state():
    with SessionLocal() as db:
        return {
            row.id: {c.name: deepcopy(getattr(row, c.name)) for c in User.__table__.columns}
            for row in db.query(User).all()
        }, db.query(AuditEvent).count()


@pytest.mark.parametrize("target", ["designer", "other"])
def test_approval_cannot_rewrite_active_accounts_or_demote_last_admin(environment, target):
    with SessionLocal() as db:
        db.get(User, "designer").role = "platform_admin"
        db.commit()
    before = state()
    response = environment.post(f"/admin/users/{target}/approve", json={"role": "solution_designer"})
    assert response.status_code == 409, response.text
    assert "pending" in response.json()["detail"].lower()
    assert state() == before
    assert environment.get("/auth/me").json()["role"] == "platform_admin"


def test_pending_approval_preserves_ownership_and_cannot_be_replayed(environment):
    with SessionLocal() as db:
        db.get(User, "designer").role = "platform_admin"
        db.get(User, "other").status = "pending"
        db.commit()
    approved = environment.post("/admin/users/other/approve", json={"role": "solution_designer"})
    assert approved.status_code == 200
    assert approved.json()["approved_by_user_id"] == "designer"
    before = state()
    duplicate = environment.post("/admin/users/other/approve", json={"role": "platform_admin"})
    assert duplicate.status_code == 409
    assert state() == before
