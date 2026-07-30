from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
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
):
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
):
    return update_contract(contract_id, payload, db)


@router.post(
    "/operation-contracts/{contract_id}/activate",
    response_model=OperationContractRead,
)
def activate_operation_contract(
    contract_id: str,
    db: Session = Depends(get_db),
):
    return activate_contract(contract_id, db)


@router.post(
    "/operation-contracts/{contract_id}/deprecate",
    response_model=OperationContractRead,
)
def deprecate_operation_contract(
    contract_id: str,
    db: Session = Depends(get_db),
):
    return deprecate_contract(contract_id, db)


@router.post(
    "/operation-contracts/{contract_id}/withdraw",
    response_model=OperationContractRead,
)
def withdraw_operation_contract(
    contract_id: str,
    db: Session = Depends(get_db),
):
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
