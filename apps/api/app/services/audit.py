import json
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.user import AuditEvent, User


def record_audit_event(
    db: Session,
    actor: User | None,
    action: str,
    target_type: str,
    target_id: str | None = None,
    details: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        id=str(uuid4()),
        actor_user_id=actor.id if actor else None,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=json.dumps(details, sort_keys=True) if details else None,
    )
    db.add(event)
    return event
