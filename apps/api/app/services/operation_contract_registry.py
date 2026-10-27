from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.operation_contract import OperationContract
from app.models.service import Service
from app.schemas.operation_contract import OperationContractCreate, OperationContractUpdate


DEPLOYMENT_ELIGIBLE_SERVICE_STATUSES = {"approved", "validated"}
CONTRACT_VERSION_UNIQUE_CONSTRAINT = (
    "uq_operation_contracts_service_identity_version"
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_service_or_404(service_id: str, db: Session, *, for_update: bool = False) -> Service:
    query = db.query(Service).filter(Service.id == service_id)
    if for_update:
        query = query.with_for_update()
    service = query.first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service


def get_contract_or_404(contract_id: str, db: Session) -> OperationContract:
    contract = (
        db.query(OperationContract)
        .filter(OperationContract.id == contract_id)
        .first()
    )
    if not contract:
        raise HTTPException(status_code=404, detail="Operation contract not found")
    return contract


def list_contracts(service_id: str, db: Session) -> list[OperationContract]:
    get_service_or_404(service_id, db)
    return (
        db.query(OperationContract)
        .filter(OperationContract.service_id == service_id)
        .order_by(OperationContract.created_at.desc())
        .all()
    )


def create_contract(
    service_id: str,
    payload: OperationContractCreate,
    db: Session,
) -> OperationContract:
    get_service_or_404(service_id, db)
    _ensure_version_is_unique(
        service_id,
        payload.operation_identity,
        payload.contract_version,
        db,
    )

    contract = OperationContract(
        service_id=service_id,
        status="draft",
        **_write_values(payload),
    )
    db.add(contract)
    _commit_changes(db)
    db.refresh(contract)
    return contract


def update_contract(
    contract_id: str,
    payload: OperationContractUpdate,
    db: Session,
) -> OperationContract:
    try:
        _, contract = _lock_service_and_contract(contract_id, db)
        if contract.status != "draft":
            raise HTTPException(
                status_code=409,
                detail="Only draft operation contracts may be updated.",
            )

        duplicate = (
            db.query(OperationContract)
            .filter(
                OperationContract.service_id == contract.service_id,
                OperationContract.operation_identity == payload.operation_identity,
                OperationContract.contract_version == payload.contract_version,
                OperationContract.id != contract.id,
            )
            .first()
        )
        if duplicate:
            raise HTTPException(
                status_code=409,
                detail="This operation contract version already exists for the service.",
            )

        for field, value in _write_values(payload).items():
            setattr(contract, field, value)
        contract.updated_at = utc_now()

        _commit_changes(db)
        db.refresh(contract)
        return contract
    except Exception:
        db.rollback()
        raise


def activate_contract(contract_id: str, db: Session) -> OperationContract:
    try:
        service, contract = _lock_service_and_contract(contract_id, db)
        if contract.status != "draft":
            raise HTTPException(
                status_code=409,
                detail="Only draft operation contracts may be activated.",
            )

        _ensure_service_is_deployment_eligible(service)

        now = utc_now()
        active_contracts = (
            db.query(OperationContract)
            .filter(
                OperationContract.service_id == contract.service_id,
                OperationContract.status == "active",
                OperationContract.id != contract.id,
            )
            .with_for_update()
            .all()
        )
        for active_contract in active_contracts:
            active_contract.status = "deprecated"
            active_contract.deprecated_at = now
            active_contract.updated_at = now

        contract.status = "active"
        contract.activated_at = now
        contract.deprecated_at = None
        contract.withdrawn_at = None
        contract.updated_at = now

        _commit_changes(db)
        db.refresh(contract)
        return contract
    except Exception:
        db.rollback()
        raise


def deprecate_contract(contract_id: str, db: Session) -> OperationContract:
    try:
        _, contract = _lock_service_and_contract(contract_id, db)
        if contract.status != "active":
            raise HTTPException(
                status_code=409,
                detail="Only active operation contracts may be deprecated.",
            )

        now = utc_now()
        contract.status = "deprecated"
        contract.deprecated_at = now
        contract.updated_at = now
        _commit_changes(db)
        db.refresh(contract)
        return contract
    except Exception:
        db.rollback()
        raise


def withdraw_contract(contract_id: str, db: Session) -> OperationContract:
    try:
        _, contract = _lock_service_and_contract(contract_id, db)
        if contract.status == "active":
            raise HTTPException(
                status_code=409,
                detail="Active operation contracts must be deprecated before withdrawal.",
            )
        if contract.status not in {"draft", "deprecated"}:
            raise HTTPException(
                status_code=409,
                detail="Only draft or deprecated operation contracts may be withdrawn.",
            )

        now = utc_now()
        contract.status = "withdrawn"
        contract.withdrawn_at = now
        contract.updated_at = now
        _commit_changes(db)
        db.refresh(contract)
        return contract
    except Exception:
        db.rollback()
        raise


def resolve_contract(service_id: str, db: Session) -> dict:
    get_service_or_404(service_id, db)
    contract = (
        db.query(OperationContract)
        .filter(
            OperationContract.service_id == service_id,
            OperationContract.status == "active",
        )
        .order_by(OperationContract.activated_at.desc())
        .first()
    )
    if not contract:
        return {
            "resolution": "unknown",
            "reason": "no_active_contract",
            "contract": None,
        }
    return {
        "resolution": "active",
        "reason": None,
        "contract": contract,
    }


def _write_values(
    payload: OperationContractCreate | OperationContractUpdate,
) -> dict:
    values = payload.model_dump()
    values["definition"] = payload.definition.model_dump(mode="json", exclude_none=True)
    return values


def _ensure_version_is_unique(
    service_id: str,
    operation_identity: str,
    contract_version: str,
    db: Session,
) -> None:
    duplicate = (
        db.query(OperationContract)
        .filter(
            OperationContract.service_id == service_id,
            OperationContract.operation_identity == operation_identity,
            OperationContract.contract_version == contract_version,
        )
        .first()
    )
    if duplicate:
        raise HTTPException(
            status_code=409,
            detail="This operation contract version already exists for the service.",
        )


def _commit_changes(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        constraint_name = getattr(
            getattr(exc.orig, "diag", None),
            "constraint_name",
            None,
        )
        if constraint_name == CONTRACT_VERSION_UNIQUE_CONSTRAINT:
            raise HTTPException(
                status_code=409,
                detail="This operation contract version already exists for the service.",
            ) from exc
        raise HTTPException(
            status_code=409,
            detail="The operation contract violates a database integrity constraint.",
        ) from exc
    except SQLAlchemyError:
        db.rollback()
        raise


def _lock_service_and_contract(
    contract_id: str,
    db: Session,
) -> tuple[Service, OperationContract]:
    contract_reference = (
        db.query(OperationContract.service_id)
        .filter(OperationContract.id == contract_id)
        .first()
    )
    if not contract_reference:
        raise HTTPException(status_code=404, detail="Operation contract not found")

    service = get_service_or_404(
        contract_reference.service_id,
        db,
        for_update=True,
    )
    contract = (
        db.query(OperationContract)
        .filter(OperationContract.id == contract_id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if not contract:
        raise HTTPException(status_code=404, detail="Operation contract not found")
    if contract.service_id != service.id:
        raise HTTPException(
            status_code=409,
            detail="The operation contract service reference changed during the request.",
        )
    return service, contract


def _ensure_service_is_deployment_eligible(service: Service) -> None:
    lifecycle_status = (service.lifecycle_status or "active").lower()
    service_status = (service.status or "").lower()
    trust_badge = (service.trust_badge or "").lower()

    if lifecycle_status == "archived":
        detail = "Contracts for archived services cannot be activated."
    elif service_status == "rejected" or trust_badge == "rejected":
        detail = "Contracts for rejected services cannot be activated."
    elif service_status not in DEPLOYMENT_ELIGIBLE_SERVICE_STATUSES:
        detail = "The service must complete governance approval before a contract can be activated."
    else:
        return

    raise HTTPException(status_code=409, detail=detail)
