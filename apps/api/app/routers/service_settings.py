from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.auth import can_manage_service, require_service_publisher
from app.models.service import Service
from app.models.user import User
from app.services.service_settings import (
    SETTINGS_KEY,
    SettingsDefinitionError,
    get_definition,
    normalize_definition,
)

router = APIRouter(tags=["service-settings"])


def _get_service(service_id: str, db: Session) -> Service:
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service


@router.get("/services/{service_id}/settings")
def read_service_settings(service_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Return the adjustable settings a service declares (null when fixed)."""
    service = _get_service(service_id, db)
    return {"service_id": service.id, "settings": get_definition(service)}


@router.put("/services/{service_id}/settings")
def write_service_settings(
    service_id: str,
    settings: dict[str, Any] | None = Body(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_service_publisher),
) -> dict[str, Any]:
    """Declare (or, with an empty body, remove) a service's adjustable settings."""
    service = _get_service(service_id, db)
    if not can_manage_service(user, service.owner_node):
        raise HTTPException(status_code=403, detail="You can only manage settings for your node's services")

    contract = dict(service.interface_contract or {})
    if settings:
        try:
            contract[SETTINGS_KEY] = normalize_definition(settings)
        except SettingsDefinitionError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    else:
        contract.pop(SETTINGS_KEY, None)

    service.interface_contract = contract
    db.commit()
    db.refresh(service)
    return {"service_id": service.id, "settings": get_definition(service)}
