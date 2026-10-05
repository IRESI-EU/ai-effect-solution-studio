from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.auth import can_manage_service, require_service_publisher
from app.models.service import Service
from app.models.user import User
from app.schemas.operation_contract import (
    OperationContractCreate,
    OperationContractRead,
    OperationContractResolution,
    OperationContractUpdate,
)
from app.services.operation_contract_registry import (
    activate_contract,
    create_contract,
    deprecate_contract,
    get_contract_or_404,
    list_contracts,
    resolve_contract,
    update_contract,
    withdraw_contract,
)


router = APIRouter(tags=["operation-contracts"])


def require_service_ownership(service_id: str, db: Session, user: User) -> None:
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    if not can_manage_service(user, service.owner_node):
        raise HTTPException(status_code=403, detail="You can only manage contracts for your node's services")


def require_contract_ownership(contract_id: str, db: Session, user: User):
    contract = get_contract_or_404(contract_id, db)
    require_service_ownership(contract.service_id, db, user)
    return contract


@router.get(
    "/services/{service_id}/operation-contracts",
    response_model=list[OperationContractRead],
)
def list_service_operation_contracts(
    service_id: str,
    db: Session = Depends(get_db),
):
    return list_contracts(service_id, db)


@router.post(
    "/services/{service_id}/operation-contracts",
    response_model=OperationContractRead,
    status_code=201,
)
def create_service_operation_contract(
    service_id: str,
    payload: OperationContractCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_service_publisher),
):
    require_service_ownership(service_id, db, user)
    return create_contract(service_id, payload, db)


@router.get(
    "/operation-contracts/{contract_id}",
    response_model=OperationContractRead,
)
def get_operation_contract(
    contract_id: str,
    db: Session = Depends(get_db),
):
    return get_contract_or_404(contract_id, db)


@router.put(
    "/operation-contracts/{contract_id}",
    response_model=OperationContractRead,
)
def update_operation_contract(
    contract_id: str,
    payload: OperationContractUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_service_publisher),
):
    require_contract_ownership(contract_id, db, user)
    return update_contract(contract_id, payload, db)


@router.post(
    "/operation-contracts/{contract_id}/activate",
    response_model=OperationContractRead,
)
def activate_operation_contract(
    contract_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_service_publisher),
):
    require_contract_ownership(contract_id, db, user)
    return activate_contract(contract_id, db)


@router.post(
    "/operation-contracts/{contract_id}/deprecate",
    response_model=OperationContractRead,
)
def deprecate_operation_contract(
    contract_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_service_publisher),
):
    require_contract_ownership(contract_id, db, user)
    return deprecate_contract(contract_id, db)


@router.post(
    "/operation-contracts/{contract_id}/withdraw",
    response_model=OperationContractRead,
)
def withdraw_operation_contract(
    contract_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_service_publisher),
):
    require_contract_ownership(contract_id, db, user)
    return withdraw_contract(contract_id, db)


@router.get(
    "/services/{service_id}/operation-contract-resolution",
    response_model=OperationContractResolution,
)
def resolve_service_operation_contract(
    service_id: str,
    db: Session = Depends(get_db),
):
    return resolve_contract(service_id, db)
