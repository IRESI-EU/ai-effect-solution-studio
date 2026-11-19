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
from app.services.parameter_values import parameter_contract_digest


router = APIRouter(tags=["operation-contracts"])


@router.get("/operation-contracts/{contract_id}/runtime-capability")
def export_runtime_capability(contract_id: str, db: Session = Depends(get_db), user: User = Depends(require_service_publisher)):
    contract = require_contract_ownership(contract_id, db, user)
    parameters = contract.definition.get('execution_parameters')
    if contract.status != "active" or not (parameters or contract.definition.get('binding_transport')=='whole-output-v1'):
        raise HTTPException(409, "Publish a parameter or supported I/O definition before exporting its runtime contract")
    service = db.query(Service).filter(Service.id == contract.service_id).first()
    from app.services.operation_contract_registry import _ensure_service_is_deployment_eligible
    _ensure_service_is_deployment_eligible(service)
    review = (service.interface_contract or {}).get("parameter_reviews", {}).get(contract.id)
    from app.services.parameter_discovery import reviewed_contract_digest, reviewed_service_digest
    if parameters and (not review or review.get("reviewed_contract_sha256") != reviewed_contract_digest(contract)
            or review.get("reviewed_service_sha256") != reviewed_service_digest(service)):
        raise HTTPException(409, "A current provider review is required before exporting runtime settings")
    if parameters:parameter_contract_digest(parameters)
    value={"capability_schema_version": "1.0", "transports": ["http-parameters-v1"] if parameters else [], "operations": [{
        "operation_name": contract.runtime_operation_name, "operation_identity": contract.operation_identity,
        "contract_version": contract.contract_version, **({'execution_parameters':parameters} if parameters else {}),
    }]}
    if contract.definition.get('binding_transport')=='whole-output-v1':
        from app.schemas.operation_contract import OperationContractDefinition
        from app.services.capability_bindings import digest
        definition=OperationContractDefinition.model_validate(contract.definition).model_dump(exclude_none=True)
        value['transports'].append('whole-output-v1')
        value['operations'][0].update(binding_transport='whole-output-v1',io_contract_sha256=digest(definition),io_definition=definition)
    return value


@router.get("/operation-contracts/{contract_id}/qualification-capability")
def export_qualification_capability(contract_id: str, db: Session = Depends(get_db), user: User = Depends(require_service_publisher)):
    contract = require_contract_ownership(contract_id, db, user)
    if contract.status != "draft" or not contract.definition.get("execution_parameters"):
        raise HTTPException(409, "Qualification requires a saved parameter draft")
    service = db.query(Service).filter(Service.id == contract.service_id).first()
    review = (service.interface_contract or {}).get("parameter_reviews", {}).get(contract.id)
    from app.services.parameter_discovery import reviewed_contract_digest, reviewed_service_digest
    if (not review or review.get("reviewed_contract_sha256") != reviewed_contract_digest(contract)
            or review.get("reviewed_service_sha256") != reviewed_service_digest(service)):
        raise HTTPException(409, "The reviewed definition or runtime changed. Repeat provider review first.")
    parameters = contract.definition["execution_parameters"]
    parameter_contract_digest(parameters)
    # Isolated node qualification only. Drafts remain unavailable to designers,
    # compilation and normal portal execution until confirmed and activated.
    return {"capability_schema_version": "1.0", "qualification_only": True,
            "transports": ["http-parameters-v1"], "operations": [{
        "operation_name": contract.runtime_operation_name, "operation_identity": contract.operation_identity,
        "contract_version": contract.contract_version, "execution_parameters": parameters,
    }]}


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
