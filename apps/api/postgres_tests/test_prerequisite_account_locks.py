"""Real PostgreSQL races on fresh test data; no runtime or external requests."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi import HTTPException

from app.models.user import User
from app.models.solution import Solution
from app.models.deployment import Deployment
from app.models.service import Service
from app.routers import admin_users as admin
from app.schemas.auth import UserUpdateRequest
from app.schemas.ownership import SolutionOwnershipRequest, UserOwnershipRequest, ServiceOwnershipRequest


def administrators(factory):
    with factory() as db:
        for identifier in ("a", "b"):
            db.get(User, identifier).role = "platform_admin"
        db.commit()


@pytest.mark.parametrize("target", ["self", "other"])
def test_concurrent_demotions_keep_one_active_administrator_and_recheck_actor(seeded, target):
    administrators(seeded)
    barrier = Barrier(2)
    def demote(identifier):
        with seeded() as db:
            actor = db.get(User, identifier)
            barrier.wait(timeout=10)
            try:
                target_id = identifier if target == "self" else ("b" if identifier == "a" else "a")
                admin.update_user(target_id, UserUpdateRequest(role="solution_designer"), db, actor)
                return 200
            except HTTPException as error:
                db.rollback()
                return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(demote, ("a", "b"))) == [200, 409 if target == "self" else 403]
    with seeded() as db:
        assert db.query(User).filter_by(role="platform_admin", status="active").count() == 1


@pytest.mark.parametrize("kind", ["solution", "deployment", "service"])
def test_concurrent_legacy_assignments_never_replace_the_first_owner(seeded, kind):
    administrators(seeded)
    with seeded() as db:
        db.get(Solution, "source-denmark").created_by_user_id = None
        db.get(Deployment, "historical").created_by_user_id = None
        db.commit()
    barrier = Barrier(2)
    def assign(identifier):
        with seeded() as db:
            actor = db.get(User, identifier)
            barrier.wait(timeout=10)
            try:
                if kind == "solution":
                    admin.assign_legacy_solution("source-denmark", SolutionOwnershipRequest(user_id=identifier), db, actor)
                elif kind == "deployment":
                    admin.assign_legacy_deployment("historical", UserOwnershipRequest(user_id=identifier), db, actor)
                else:
                    admin.assign_legacy_service("denmark-GenerateTopology", ServiceOwnershipRequest(node="denmark" if identifier == "a" else "portugal"), db, actor)
                return 200
            except HTTPException as error:
                db.rollback()
                return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(assign, ("a", "b"))) == [200, 409]
    with seeded() as db:
        if kind == "solution":
            assert db.get(Solution, "source-denmark").created_by_user_id in {"a", "b"}
            assert db.get(Deployment, "historical").created_by_user_id == db.get(Solution, "source-denmark").created_by_user_id
        elif kind == "deployment":
            assert db.get(Deployment, "historical").created_by_user_id in {"a", "b"}
        else:
            assert db.get(Service, "denmark-GenerateTopology").owner_node in {"denmark", "portugal"}
