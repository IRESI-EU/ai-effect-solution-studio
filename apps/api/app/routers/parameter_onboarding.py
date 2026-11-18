"""Ordinary node-owned onboarding; discovery never activates runtime support."""
from copy import deepcopy
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.auth import can_manage_service, require_service_publisher
from app.models.user import User
from app.schemas.operation_contract import OperationContractCreate, OperationContractRead
from app.schemas.parameter_onboarding import ParameterDiscoveryRequest, ParameterReviewRequest, RuntimeConfirmationRequest
from app.services.audit import record_audit_event
from app.services.operation_contract_registry import create_contract, get_service_or_404, resolve_contract
from app.services.parameter_discovery import discover, reviewed_contract_digest, reviewed_service_digest, validate_reviewed_definition
from app.services.parameter_values import parameter_contract_digest


router = APIRouter(tags=["parameter-onboarding"])


def owned_service(service_id: str, db: Session, user: User, *, for_update: bool = False):
    service = get_service_or_404(service_id, db, for_update=for_update)
    if not can_manage_service(user, service.owner_node):
        raise HTTPException(403, "You can only review parameters for your node's services")
    return service


@router.get("/services/{service_id}/parameter-onboarding")
def get_parameter_onboarding(service_id: str, db: Session = Depends(get_db), user: User = Depends(require_service_publisher)):
    service = owned_service(service_id, db, user)
    metadata = service.interface_contract or {}
    return {"service_id": service.id, "operation_name": service.operation_name,
            "interface_type": service.interface_type, "service_status": service.status,
            "discovery": metadata.get("parameter_discovery"), "reviews": metadata.get("parameter_reviews", {})}


@router.post("/services/{service_id}/parameter-onboarding/discover")
def discover_parameters(service_id: str, payload: ParameterDiscoveryRequest, db: Session = Depends(get_db), user: User = Depends(require_service_publisher)):
    service = owned_service(service_id, db, user, for_update=True)
    try:
        discovery = discover(payload.document, payload.source_reference, service.operation_name, payload.operation_id)
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from exc
    service.interface_contract = {**(service.interface_contract or {}), "parameter_discovery": discovery}
    record_audit_event(db, user, "service.parameters_discovered", "service", service.id,
                       {"source_sha256": discovery["source_sha256"], "revision": discovery["revision"]})
    db.commit()
    return discovery


@router.post("/services/{service_id}/parameter-onboarding/review", response_model=OperationContractRead, status_code=201)
def review_parameters(service_id: str, payload: ParameterReviewRequest, db: Session = Depends(get_db), user: User = Depends(require_service_publisher)):
    service = owned_service(service_id, db, user, for_update=True)
    metadata = deepcopy(service.interface_contract or {})
    discovery = metadata.get("parameter_discovery")
    if not discovery or discovery["revision"] != payload.discovery_revision or discovery["operation_name"] != service.operation_name:
        raise HTTPException(409, "The interface review changed. Reload and rediscover the operation before saving.")
    if any((payload.runtime_support_confirmed, payload.normal_configuration_tested, payload.invalid_configuration_tested)) and not payload.evidence_reference.strip():
        raise HTTPException(422, "Supply the provider's runtime test evidence reference")
    candidates = {(c["name"], c["source_pointer"]): c for c in discovery["candidates"]}
    properties, mappings = {}, {}
    for parameter in payload.parameters:
        candidate = candidates.get((parameter.name, parameter.source_pointer))
        if not candidate or not candidate["supported"] or candidate["classification"] != "setting":
            raise HTTPException(422, "Select a supported candidate from the current interface description")
        if parameter.name in properties:
            raise HTTPException(422, "Parameter names must be unique")
        try:
            validate_reviewed_definition(parameter.name, parameter.definition)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        if not parameter.algorithm_mapping.strip():
            raise HTTPException(422, "Confirm how each value reaches the algorithm")
        properties[parameter.name] = parameter.definition.model_dump(mode="json", exclude_none=True)
        # Mapping is descriptive. The existing transport always uses this key.
        mappings[parameter.name] = {"transport_path": f"configuration.parameters.{parameter.name}",
                                    "algorithm_mapping": parameter.algorithm_mapping.strip(),
                                    "source_pointer": parameter.source_pointer,
                                    "unit": parameter.definition.unit, "source_location": candidate.get("source_location", "json_schema")}
    current = resolve_contract(service_id, db)["contract"]
    definition = deepcopy(current.definition) if current else {"operation_role": payload.operation_role}
    definition["execution_parameters"] = {"schema_version": "1.0", "transport": "http-parameters-v1", "properties": properties}
    try:
        contract_payload = OperationContractCreate(
            operation_identity=payload.operation_identity, runtime_operation_name=service.operation_name,
            contract_version=payload.contract_version, source_kind="manifest",
            source_reference=discovery["source_reference"], definition=definition)
        # Check the same capability digest used by compiler/runtime negotiation.
        parameter_contract_digest(contract_payload.definition.execution_parameters.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    try:
        contract = create_contract(service_id, contract_payload, db, commit=False)
        review = {"contract_id": contract.id, "discovery_revision": discovery["revision"],
                  "source_sha256": discovery["source_sha256"], "source_reference": discovery["source_reference"],
                  "reviewed_by": user.id, "reviewed_at": datetime.now(timezone.utc).isoformat(),
                  "evidence_reference": payload.evidence_reference.strip(), "mappings": mappings,
                  "runtime_support_confirmed": payload.runtime_support_confirmed, "normal_configuration_tested": payload.normal_configuration_tested, "invalid_configuration_tested": payload.invalid_configuration_tested,
                  "reviewed_service_sha256": reviewed_service_digest(service),
                  "reviewed_contract_sha256": reviewed_contract_digest(contract)}
        metadata.setdefault("parameter_reviews", {})[contract.id] = review
        service.interface_contract = metadata
        record_audit_event(db, user, "service.parameters_reviewed", "service", service.id,
                           {"contract_id": contract.id, "source_sha256": discovery["source_sha256"]})
        db.commit()
        db.refresh(contract)
        return contract
    except Exception:
        db.rollback()
        raise


@router.post("/services/{service_id}/parameter-onboarding/reviews/{contract_id}/confirm-runtime")
def confirm_runtime(service_id: str, contract_id: str, payload: RuntimeConfirmationRequest,
                    db: Session = Depends(get_db), user: User = Depends(require_service_publisher)):
    service = owned_service(service_id, db, user, for_update=True)
    from app.services.operation_contract_registry import get_contract_or_404
    contract = get_contract_or_404(contract_id, db)
    if contract.service_id != service_id:
        raise HTTPException(404, "Review not found for this service")
    if contract.status != "draft":
        raise HTTPException(409, "Runtime qualification applies to a saved draft")
    metadata = deepcopy(service.interface_contract or {})
    review = metadata.get("parameter_reviews", {}).get(contract_id)
    if (not review or payload.reviewed_contract_sha256 != reviewed_contract_digest(contract)
            or review.get("reviewed_contract_sha256") != reviewed_contract_digest(contract)
            or review.get("reviewed_service_sha256") != reviewed_service_digest(service)):
        raise HTTPException(409, "The reviewed definition or runtime changed. Repeat provider review before confirmation.")
    if not all((payload.runtime_support_confirmed, payload.normal_configuration_tested, payload.invalid_configuration_tested)) or not payload.evidence_reference.strip():
        raise HTTPException(422, "Confirm runtime consumption, normal and invalid checks with an evidence reference")
    review.update({"runtime_support_confirmed": True, "normal_configuration_tested": True,
                   "invalid_configuration_tested": True, "evidence_reference": payload.evidence_reference.strip(),
                   "runtime_confirmed_by": user.id, "runtime_confirmed_at": datetime.now(timezone.utc).isoformat()})
    service.interface_contract = metadata
    record_audit_event(db, user, "service.parameter_runtime_confirmed", "service", service.id, {"contract_id": contract_id})
    db.commit()
    return review
