"""Save each run's gRPC outputs as soon as its tasks complete.

After a workflow is submitted, ``watch_workflow`` polls the orchestrator in
the background. Each completed task's gRPC output is decoded once (see
grpc_preview) and stored in ``run_output_snapshots``. The Deployments page
then shows that run's own result, even after later runs have replaced the
service's in-memory copy.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import SessionLocal
from app.models.run_output_snapshot import RunOutputSnapshot
from app.services.data_reference_service import preview_data_reference
from app.services.orchestrator_adapter import get_workflow_status, get_workflow_tasks

logger = logging.getLogger(__name__)

SNAPSHOT_PROTOCOLS = {"grpc"}
TERMINAL_STATUSES = {"completed", "failed"}
TRIM_LIST_ITEMS = 20
TRIM_STRING_CHARS = 2000


def _trim(value: Any) -> Any:
    """Shorten long lists and strings, keeping the structure readable."""
    if isinstance(value, dict):
        return {key: _trim(item) for key, item in value.items()}
    if isinstance(value, list):
        trimmed = [_trim(item) for item in value[:TRIM_LIST_ITEMS]]
        if len(value) > TRIM_LIST_ITEMS:
            trimmed.append(f"... {len(value) - TRIM_LIST_ITEMS} more items not saved")
        return trimmed
    if isinstance(value, str) and len(value) > TRIM_STRING_CHARS:
        return value[:TRIM_STRING_CHARS] + f"... ({len(value) - TRIM_STRING_CHARS} more characters not saved)"
    return value


def fit_to_size_cap(preview: dict, max_bytes: int | None = None) -> dict:
    """Return the preview, trimmed if its JSON exceeds the size cap."""
    max_bytes = settings.run_snapshot_max_bytes if max_bytes is None else max_bytes
    size = len(json.dumps(preview, ensure_ascii=False, default=str).encode("utf-8"))
    if size <= max_bytes:
        return preview
    trimmed = {**preview, "content": _trim(preview.get("content"))}
    trimmed["truncated"] = True
    trimmed["original_size_bytes"] = size
    if len(json.dumps(trimmed, ensure_ascii=False, default=str).encode("utf-8")) > max_bytes:
        trimmed["content"] = None
    return trimmed


def delete_expired_snapshots(db: Session, retention_days: int | None = None) -> int:
    """Delete saved outputs older than the retention period (0 = keep forever)."""
    days = settings.run_snapshot_retention_days if retention_days is None else retention_days
    if days <= 0:
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    deleted = (
        db.query(RunOutputSnapshot)
        .filter(RunOutputSnapshot.captured_at < cutoff)
        .delete(synchronize_session=False)
    )
    db.commit()
    return deleted


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
                preview=fit_to_size_cap(preview),
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
            try:
                with session_factory() as db:
                    delete_expired_snapshots(db)
            except Exception:
                logger.exception("Could not clean up expired run outputs")
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
    note = f"Saved from this run when the step completed ({captured})."
    if row.preview.get("truncated"):
        size_mb = row.preview.get("original_size_bytes", 0) / 1_048_576
        note += f" The full result ({size_mb:.1f} MB) was larger than the saving limit, so long lists and texts were shortened."
    return {**row.preview, "note": note, "snapshot": True}
