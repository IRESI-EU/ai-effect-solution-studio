import hashlib
import json

from fastapi import HTTPException
from app.models.execution_submission import ExecutionSubmission
from app.core.config import settings


def prepare(db, user, workflow, compiled):
    value = {"request": workflow.model_dump(mode="json", exclude_unset=True),
             "compiled": compiled, "runtime_destination": settings.orchestrator_base_url}
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)
    row = ExecutionSubmission(owner_user_id=user.id, solution_id=workflow.solution_id,
                              submitted=json.loads(encoded), submitted_sha256=hashlib.sha256(encoded.encode()).hexdigest())
    db.add(row)
    db.commit()
    return row


def view(row):
    encoded = json.dumps(row.submitted, sort_keys=True, ensure_ascii=False, allow_nan=False)
    if hashlib.sha256(encoded.encode()).hexdigest() != row.submitted_sha256:
        raise HTTPException(409, "Submitted execution snapshot failed its integrity check")
    return {"id": row.id, "workflow_id": row.workflow_id, "phase": row.phase,
            "submitted_sha256": row.submitted_sha256, "submitted": row.submitted,
            "evidence_level": "validated_submission", "consumption": "not verified by this snapshot"}
