"""Save each run's gRPC outputs as soon as its tasks complete.

After a workflow is submitted, ``watch_workflow`` polls the orchestrator in
the background. Each completed task's gRPC output is decoded once (see
grpc_preview) and stored in ``run_output_snapshots``. The Deployments page
then shows that run's own result, even after later runs have replaced the
service's in-memory copy.
"""

from __future__ import annotations

import logging
import time
from typing import Callable

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.run_output_snapshot import RunOutputSnapshot
from app.services.data_reference_service import preview_data_reference
from app.services.orchestrator_adapter import get_workflow_status, get_workflow_tasks

logger = logging.getLogger(__name__)

SNAPSHOT_PROTOCOLS = {"grpc"}
TERMINAL_STATUSES = {"completed", "failed"}


def _tasks_of(payload) -> list[dict]:
    if isinstance(payload, dict):
        return payload.get("tasks") or []
    return payload or []


def capture_completed_tasks(db: Session, workflow_id: str, tasks: list[dict]) -> int:
    """Store snapshots for completed tasks that do not have one yet."""
    existing = {
        (row.task_id, row.uri)
        for row in db.query(RunOutputSnapshot.task_id, RunOutputSnapshot.uri)
        .filter(RunOutputSnapshot.workflow_id == workflow_id)
        .all()
    }
    saved = 0
    for task in tasks:
        if task.get("status") != "completed":
            continue
        for ref in task.get("output_refs") or []:
            protocol = (ref.get("protocol") or "").lower()
            uri = ref.get("uri") or ""
            if protocol not in SNAPSHOT_PROTOCOLS or (task["task_id"], uri) in existing:
                continue
            preview = preview_data_reference(
                protocol, uri, task["task_id"], format_hint=ref.get("format"), db=db
            )
            if not preview.get("available"):
                continue
            db.add(RunOutputSnapshot(
                workflow_id=workflow_id,
                task_id=task["task_id"],
                node_key=task.get("node_key"),
                protocol=protocol,
                uri=uri,
                format=ref.get("format"),
                preview=preview,
            ))
            try:
                db.commit()
                saved += 1
                existing.add((task["task_id"], uri))
            except IntegrityError:
                db.rollback()
    return saved


def watch_workflow(
    workflow_id: str,
    *,
    interval: float = 2.0,
    timeout: float = 3600.0,
    session_factory: Callable[[], Session] = SessionLocal,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Poll a workflow until it ends, saving outputs as tasks complete."""
    deadline = time.monotonic() + timeout
    while True:
        try:
            status = (get_workflow_status(workflow_id) or {}).get("status")
            tasks = _tasks_of(get_workflow_tasks(workflow_id))
            with session_factory() as db:
                capture_completed_tasks(db, workflow_id, tasks)
        except Exception:  # never let a background watcher crash the API
            logger.exception("Could not capture outputs for workflow %s", workflow_id)
            status = None
        if status in TERMINAL_STATUSES or time.monotonic() >= deadline:
            return
        sleep(interval)


def saved_preview(db: Session, workflow_id: str, task_id: str, uri: str) -> dict | None:
    row = (
        db.query(RunOutputSnapshot)
        .filter(
            RunOutputSnapshot.workflow_id == workflow_id,
            RunOutputSnapshot.task_id == task_id,
            RunOutputSnapshot.uri == uri,
        )
        .first()
    )
    if row is None:
        return None
    captured = row.captured_at.strftime("%d %b %Y %H:%M:%S UTC") if row.captured_at else "run time"
    return {
        **row.preview,
        "note": f"Saved from this run when the step completed ({captured}).",
        "snapshot": True,
    }
