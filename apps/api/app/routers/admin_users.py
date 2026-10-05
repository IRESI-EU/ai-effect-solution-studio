from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.auth import require_admin
from app.models.user import AuditEvent, User, UserSession
from app.models.deployment import Deployment
from app.models.service import Service
from app.models.solution import Solution
from app.schemas.auth import ApprovalRequest, AuditEventRead, UserRead, UserUpdateRequest
from app.schemas.ownership import ServiceOwnershipRequest, SolutionOwnershipRequest, UserOwnershipRequest
from app.services.audit import record_audit_event


router = APIRouter(prefix="/admin", tags=["administration"])


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _get_user_or_404(user_id: str, db: Session) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _active_admin_count(db: Session) -> int:
    return (
        db.query(User)
        .filter(User.role == "platform_admin", User.status == "active")
        .count()
    )


def _get_active_user_or_404(user_id: str, db: Session) -> User:
    user = _get_user_or_404(user_id, db)
    if user.status != "active":
        raise HTTPException(status_code=409, detail="Ownership can only be assigned to an active user")
    return user


@router.get("/users", response_model=list[UserRead])
def list_users(
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    query = db.query(User)
    if status:
        query = query.filter(User.status == status)
    return query.order_by(User.created_at.desc()).all()


@router.post("/users/{user_id}/approve", response_model=UserRead)
def approve_user(
    user_id: str,
    payload: ApprovalRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = _get_user_or_404(user_id, db)
    user.role = payload.role
    user.node = payload.node if payload.role != "platform_admin" else None
    user.status = "active"
    user.approved_at = utc_now()
    user.approved_by_user_id = admin.id
    record_audit_event(
        db,
        admin,
        "user.approved",
        "user",
        user.id,
        {"role": user.role, "node": user.node, "email": user.email},
    )
    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/reject", response_model=UserRead)
def reject_user(
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = _get_user_or_404(user_id, db)
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot reject your own account")
    user.status = "rejected"
    db.query(UserSession).filter(UserSession.user_id == user.id).delete()
    record_audit_event(db, admin, "user.rejected", "user", user.id, {"email": user.email})
    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/suspend", response_model=UserRead)
def suspend_user(
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = _get_user_or_404(user_id, db)
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot suspend your own account")
    if user.role == "platform_admin" and user.status == "active" and _active_admin_count(db) <= 1:
        raise HTTPException(status_code=409, detail="At least one active administrator is required")
    user.status = "suspended"
    db.query(UserSession).filter(UserSession.user_id == user.id).delete()
    record_audit_event(db, admin, "user.suspended", "user", user.id, {"email": user.email})
    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/reactivate", response_model=UserRead)
def reactivate_user(
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = _get_user_or_404(user_id, db)
    user.status = "active"
    user.approved_at = user.approved_at or utc_now()
    user.approved_by_user_id = admin.id
    record_audit_event(db, admin, "user.reactivated", "user", user.id, {"email": user.email})
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: str,
    payload: UserUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = _get_user_or_404(user_id, db)
    previous_role = user.role
    if payload.display_name is not None:
        user.display_name = payload.display_name.strip()
    if payload.role is not None:
        if (
            user.id == admin.id
            and user.role == "platform_admin"
            and payload.role != "platform_admin"
            and _active_admin_count(db) <= 1
        ):
            raise HTTPException(status_code=409, detail="At least one active administrator is required")
        user.role = payload.role
        if payload.role == "platform_admin":
            user.node = None
    if payload.node is not None or payload.role == "platform_admin":
        user.node = payload.node if user.role != "platform_admin" else None
    if user.role == "node_manager" and not user.node:
        raise HTTPException(status_code=422, detail="A Node Manager must be assigned to a node")
    record_audit_event(
        db,
        admin,
        "user.updated",
        "user",
        user.id,
        {"previous_role": previous_role, "role": user.role, "node": user.node},
    )
    db.commit()
    db.refresh(user)
    return user


@router.get("/audit-events", response_model=list[AuditEventRead])
def list_audit_events(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return db.query(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit).all()


@router.get("/ownership/unassigned")
def list_unassigned_records(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    solutions = (
        db.query(Solution)
        .filter(Solution.created_by_user_id.is_(None))
        .order_by(Solution.updated_at.desc())
        .all()
    )
    deployments = (
        db.query(Deployment)
        .filter(Deployment.created_by_user_id.is_(None))
        .order_by(Deployment.created_at.desc())
        .all()
    )
    services = (
        db.query(Service)
        .filter(Service.owner_node.is_(None))
        .order_by(Service.provider.asc(), Service.name.asc())
        .all()
    )
    return {
        "solutions": [
            {"id": item.id, "name": item.name, "status": item.status, "updated_at": item.updated_at}
            for item in solutions
        ],
        "deployments": [
            {
                "id": item.id,
                "name": item.name,
                "workflow_id": item.workflow_id,
                "solution_id": item.solution_id,
                "status": item.status,
                "created_at": item.created_at,
            }
            for item in deployments
        ],
        "services": [
            {"id": item.id, "name": item.name, "provider": item.provider, "status": item.status}
            for item in services
        ],
    }


@router.post("/ownership/solutions/{solution_id}/assign")
def assign_legacy_solution(
    solution_id: str,
    payload: SolutionOwnershipRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    owner = _get_active_user_or_404(payload.user_id, db)
    solution = db.query(Solution).filter(Solution.id == solution_id).first()
    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")
    if solution.created_by_user_id is not None:
        raise HTTPException(status_code=409, detail="This solution already has an owner")
    solution.created_by_user_id = owner.id
    assigned_deployments = 0
    if payload.include_unowned_deployments:
        assigned_deployments = (
            db.query(Deployment)
            .filter(
                Deployment.solution_id == solution.id,
                Deployment.created_by_user_id.is_(None),
            )
            .update({Deployment.created_by_user_id: owner.id}, synchronize_session=False)
        )
    record_audit_event(
        db,
        admin,
        "ownership.legacy_solution_assigned",
        "solution",
        solution.id,
        {"owner_user_id": owner.id, "linked_deployments": assigned_deployments},
    )
    db.commit()
    return {"status": "assigned", "solution_id": solution.id, "owner_user_id": owner.id, "linked_deployments": assigned_deployments}


@router.post("/ownership/deployments/{deployment_id}/assign")
def assign_legacy_deployment(
    deployment_id: str,
    payload: UserOwnershipRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    owner = _get_active_user_or_404(payload.user_id, db)
    deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    if deployment.created_by_user_id is not None:
        raise HTTPException(status_code=409, detail="This deployment already has an owner")
    deployment.created_by_user_id = owner.id
    record_audit_event(
        db,
        admin,
        "ownership.legacy_deployment_assigned",
        "deployment",
        deployment.id,
        {"owner_user_id": owner.id},
    )
    db.commit()
    return {"status": "assigned", "deployment_id": deployment.id, "owner_user_id": owner.id}


@router.post("/ownership/services/{service_id}/assign")
def assign_legacy_service(
    service_id: str,
    payload: ServiceOwnershipRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    if service.owner_node is not None:
        raise HTTPException(status_code=409, detail="This service already has a node owner")
    service.owner_node = payload.node
    record_audit_event(
        db,
        admin,
        "ownership.legacy_service_assigned",
        "service",
        service.id,
        {"owner_node": payload.node},
    )
    db.commit()
    return {"status": "assigned", "service_id": service.id, "owner_node": service.owner_node}
