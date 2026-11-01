"""One-time synthetic bootstrap. Never imports the API server or runs a workflow."""
import json
import os
from datetime import datetime, UTC
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User
from app.models.service import Service
from app.models.solution import Solution
from app.models.deployment import Deployment
from app.schemas.auth import validate_password_strength
from app.services.audit import record_audit_event
from app.services.solution_design import build_linear_builder_design


def seed(db, environment=None):
    environment = os.environ if environment is None else environment
    url = make_url(settings.database_url)
    if (url.database != "design_ai_staging" or url.host != "postgres"
            or environment.get("STAGING_REVIEW_SEED") != "synthetic-only"
            or settings.design_ai_enabled or settings.design_ai_dutch_demo or settings.aie37_qualification
            or settings.openai_api_key or settings.design_ai_demo_execution_grant_file
            or settings.design_ai_acceptance_budget_file or settings.design_ai_acceptance_task_limit_file):
        raise RuntimeError("Synthetic bootstrap requires the fresh disconnected staging configuration")
    if db.execute(text("SELECT current_database()")).scalar_one() != "design_ai_staging":
        raise RuntimeError("Unexpected database; no bootstrap attempted")
    if any(db.query(model).first() is not None for model in (User, Service, Solution, Deployment)):
        raise RuntimeError("Staging data already exists; preserve it. Bootstrap never resets accounts or records")
    pairs = [(environment["STAGING_DESIGNER_A_EMAIL"], environment["STAGING_DESIGNER_A_PASSWORD"]),
             (environment["STAGING_DESIGNER_B_EMAIL"], environment["STAGING_DESIGNER_B_PASSWORD"])]
    for email, password in pairs:
        if not email.endswith("@staging.invalid"):
            raise RuntimeError("Use new staging-only synthetic account identifiers")
        validate_password_strength(password)
    validate_password_strength(settings.bootstrap_admin_password)
    if not settings.bootstrap_admin_email.endswith("@staging.invalid"):
        raise RuntimeError("Use a new staging-only administrator")
    if len({settings.bootstrap_admin_email, *[email for email, _ in pairs]}) != 3:
        raise RuntimeError("Synthetic account identifiers must be distinct")
    # One transaction; no existing bootstrap helper that commits halfway through.
    administrator = User(id=str(uuid4()), email=settings.bootstrap_admin_email,
        display_name="Staging review administrator", password_hash=hash_password(settings.bootstrap_admin_password),
        role="platform_admin", status="active", approved_at=datetime.now(UTC).replace(tzinfo=None))
    db.add(administrator)
    record_audit_event(db, None, "staging.synthetic_bootstrap", "user", administrator.id)
    service = Service(id=str(uuid4()), name="Synthetic review module — disconnected",
        provider="Synthetic staging fixture", category="Review", description="Portal review only; no runtime is deployed.",
        input_type="JSON", output_type="JSON", status="approved", lifecycle_status="active",
        operation_name="ReviewSample", container_name="synthetic-review-only", image="", proto_uri="synthetic-only.proto")
    db.add(service)
    for label, (email, password) in zip(("A", "B"), pairs, strict=True):
        user = User(id=str(uuid4()), email=email, display_name=f"Staging reviewer {label}",
            password_hash=hash_password(password), role="solution_designer", status="active")
        db.add(user)
        nodes, edges = build_linear_builder_design({"sample": service}, [])
        db.add(Solution(id=str(uuid4()), name=f"Synthetic disconnected review {label}",
            description="Synthetic portal/ownership review. No experiment has executed.", nodes=nodes, edges=edges,
            status="draft", created_by_user_id=user.id, design_metadata={"synthetic_staging_review": True}))
    db.commit()
    return {"synthetic_only": True, "accounts": 3, "solutions": 2, "services": 1, "workflow_executions": 0}


if __name__ == "__main__":
    from app.db import SessionLocal
    with SessionLocal() as session:
        print(json.dumps(seed(session)))
