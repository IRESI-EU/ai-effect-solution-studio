from datetime import datetime, timezone
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.db import Base, SessionLocal, engine, get_db
from app.models.deployment import Deployment
from app.models.operation_contract import OperationContract
from app.models.service import Service
from app.models.solution import Solution
from app.models.user import User
from app.dependencies.auth import (
    can_manage_owned_record,
    can_manage_service,
    get_current_user,
    get_optional_user,
    require_admin,
    require_service_publisher,
)
from app.routers.auth import bootstrap_admin, router as auth_router
from app.routers.admin_users import router as admin_users_router
from app.routers.operation_contracts import router as operation_contracts_router
from app.schemas.data_reference import DataReferencePreviewRequest
from app.schemas.deployment import (
    DeploymentCreate,
    DeploymentRead,
    DeploymentUpdate,
)
from app.schemas.service import (
    RuntimeVerificationRead,
    ServiceCreate,
    ServiceRead,
    ServiceTechnicalMetadataUpdate,
)
from app.schemas.solution import (
    SolutionCreate,
    SolutionRead,
    SolutionUpdate,
    SolutionWithDeploymentsRead,
)
from app.schemas.workflow_submit import WorkflowSubmitRequest
from app.schemas.wp3_import import WP3ImportRequest
from app.services.data_reference_service import preview_data_reference
from app.services.orchestrator_adapter import (
    get_workflow_status,
    get_workflow_tasks,
    submit_to_orchestrator,
)
from app.services.runtime_preflight import (
    build_runtime_health_url,
    check_service_runtime,
    run_runtime_preflight,
)
from app.services.workflow_compiler import compile_to_wp3_payload
from app.services.wp3_importer import import_wp3_package
from app.schemas.service_import import (
    ServiceImportManualConfirmRequest,
    ServiceImportManualPreviewRequest,
    ServiceImportPreviewRequest,
    ServiceImportPreviewResponse,
)
from app.services.service_manifest_importer import normalize_manifest, preview_service_manifest
from app.services.audit import record_audit_event


Base.metadata.create_all(bind=engine)

with SessionLocal() as bootstrap_db:
    bootstrap_admin(bootstrap_db)

app = FastAPI(title="AI-EFFECT Solution Studio API", version="0.1.0")
app.include_router(operation_contracts_router)
app.include_router(auth_router)
app.include_router(admin_users_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:13000",
        "http://127.0.0.1:13000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def touch_updated_at(record):
    if hasattr(record, "updated_at"):
        record.updated_at = datetime.utcnow()


def store_runtime_verification(service: Service, result: dict) -> dict:
    evidence = {
        "status": "verified" if result["status"] == "ready" else "failed",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "runtime_url": result.get("runtime_url"),
        "http_status": result.get("http_status"),
        "failure_reason": result.get("failure_reason"),
        "message": result["message"],
        "address": {
            "internal_host": service.internal_host,
            "internal_port": service.internal_port,
            "health_path": service.health_path,
        },
    }
    contract = dict(service.interface_contract or {})
    contract["runtime_verification"] = evidence
    service.interface_contract = contract
    return evidence


def invalidate_runtime_verification(service: Service, reason: str) -> dict:
    evidence = {
        "status": "not_verified",
        "invalidated_at": datetime.now(timezone.utc).isoformat(),
        "runtime_url": None,
        "http_status": None,
        "failure_reason": "metadata_changed",
        "message": reason,
    }
    contract = dict(service.interface_contract or {})
    contract["runtime_verification"] = evidence
    service.interface_contract = contract
    return evidence


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/admin/import/wp3-package")
def admin_import_wp3_package(
    payload: WP3ImportRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return import_wp3_package(payload, db)


@app.post("/data-references/preview")
def preview_data_reference_endpoint(
    payload: DataReferencePreviewRequest,
    _: User = Depends(get_current_user),
):
    return preview_data_reference(payload.protocol, payload.uri, payload.task_id)


# ---------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------

@app.get("/services", response_model=list[ServiceRead])
def list_services(
    include_archived: bool = False,
    archived_only: bool = False,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    if include_archived or archived_only:
        if not user or user.role not in {"platform_admin", "node_manager"}:
            raise HTTPException(status_code=403, detail="Service management access is required")
    services_exist = db.query(Service).first()

    if not services_exist:
        seed_services(db)

    query = db.query(Service)

    if user and user.role == "node_manager" and (include_archived or archived_only):
        query = query.filter(Service.owner_node == user.node)

    if archived_only:
        query = query.filter(Service.lifecycle_status == "archived")
    elif not include_archived:
        query = query.filter(Service.lifecycle_status != "archived")

    return query.order_by(Service.name.asc()).all()


@app.post("/services", response_model=ServiceRead)
def create_service(
    payload: ServiceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_service_publisher),
):
    service = Service(
        id=str(uuid4()),
        name=payload.name,
        provider=payload.provider,
        category=payload.category,
        description=payload.description,
        input_type=payload.input_type,
        output_type=payload.output_type,
        version=payload.version,
        status="pending_review",
        lifecycle_status="active",
        trust_badge="Awaiting validation",
        container_name=payload.container_name,
        image=payload.image,
        proto_uri=payload.proto_uri,
        node_type=payload.node_type,
        operation_name=payload.operation_name,
        input_message_name=payload.input_message_name,
        output_message_name=payload.output_message_name,
        internal_host=payload.internal_host or payload.container_name,
        internal_port=payload.internal_port,
        owner_node=user.node,
        created_by_user_id=user.id,
    )

    db.add(service)
    record_audit_event(db, user, "service.created", "service", service.id, {"node": service.owner_node})
    db.commit()
    db.refresh(service)

    return service
@app.post("/services/import/preview", response_model=ServiceImportPreviewResponse)
def preview_service_import(
    request: ServiceImportPreviewRequest,
    _: User = Depends(require_service_publisher),
):
    return preview_service_manifest(
        repo_url=request.repo_url,
        branch=request.branch,
        manifest_path=request.manifest_path,
    )

@app.post("/services/import/preview-manual", response_model=ServiceImportPreviewResponse)
def preview_manual_service_import(
    request: ServiceImportManualPreviewRequest,
    _: User = Depends(require_service_publisher),
):
    validation = []
    service = normalize_manifest(
        manifest=request.manifest,
        repo_url=request.repo_url,
        branch=request.branch,
        manifest_path=request.manifest_path,
        validation=validation,
    )

    has_errors = any(item.level == "error" for item in validation)
    has_warnings = any(item.level == "warning" for item in validation)

    if has_errors:
        status = "invalid"
    elif has_warnings:
        status = "warning"
    else:
        status = "valid"

    return ServiceImportPreviewResponse(
        status=status,
        raw_manifest=request.manifest,
        service=None if has_errors else service,
        validation=validation,
    )

@app.post("/services/import/confirm-manual", response_model=ServiceRead)
def confirm_manual_service_import(
    request: ServiceImportManualConfirmRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_service_publisher),
):
    if request.onboarding and not request.onboarding.registration_only_acknowledged:
        raise HTTPException(
            status_code=422,
            detail="Confirm that catalogue registration does not deploy or activate the service.",
        )

    validation = []
    imported = normalize_manifest(
        manifest=request.manifest,
        repo_url=request.repo_url,
        branch=request.branch,
        manifest_path=request.manifest_path,
        validation=validation,
    )

    has_errors = any(item.level == "error" for item in validation)
    if has_errors:
        raise HTTPException(
            status_code=400,
            detail=[item.model_dump() for item in validation],
        )

    service_id = imported.id or f"svc-imported-{uuid4().hex[:12]}"

    existing = db.query(Service).filter(Service.id == service_id).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Service with id '{service_id}' already exists.",
        )

    interface_contract = dict(imported.interface_contract or {})
    if request.onboarding:
        interface_contract["onboarding"] = request.onboarding.model_dump()

    service = Service(
     id=service_id,
     name=imported.name,
     provider=imported.provider,
     category=imported.category,
     version=imported.version,
     description=imported.description,
     status="pending_review",
     trust_badge="pending_review",
     lifecycle_status="active",

     repository_url=imported.repository_url,
     repository_branch=imported.repository_branch,
     manifest_path=imported.manifest_path,
     interface_type=imported.interface_type,
     interface_contract=interface_contract,
     orchestration_mode=imported.orchestration_mode,
     adapter_type=imported.adapter_type,
     health_path=imported.health_path,
     contract_uri=imported.contract_uri,

     container_name=imported.container_name,
     image=imported.image or "",
     proto_uri=imported.proto_uri or imported.contract_uri or request.manifest_path,
     node_type="MLModel",
     operation_name=imported.operation_name,
     input_message_name=imported.input_message_name,
     output_message_name=imported.output_message_name,
     input_type=imported.input_type,
     output_type=imported.output_type,
     internal_host=imported.internal_host,
     internal_port=imported.internal_port,
     owner_node=user.node,
     created_by_user_id=user.id,
 )

    db.add(service)
    record_audit_event(db, user, "service.imported", "service", service.id, {"node": service.owner_node})
    db.commit()
    db.refresh(service)

    return service


def update_service_review(
    service_id: str,
    status: str,
    trust_badge: str,
    db: Session,
    actor: User,
):
    service = db.query(Service).filter(Service.id == service_id).first()

    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    service.status = status
    service.trust_badge = trust_badge

    runtime_result = None
    if status == "approved":
        runtime_result = check_service_runtime(service)
        store_runtime_verification(service, runtime_result)

    if service.lifecycle_status != "archived":
        service.lifecycle_status = "active"

    touch_updated_at(service)
    record_audit_event(
        db,
        actor,
        f"service.review_{status}",
        "service",
        service.id,
        {
            "status": status,
            "runtime_verification": runtime_result["status"] if runtime_result else None,
            "runtime_failure_reason": runtime_result.get("failure_reason") if runtime_result else None,
        },
    )
    db.commit()
    db.refresh(service)

    return service


@app.post("/services/{service_id}/review/approve", response_model=ServiceRead)
def approve_service_review(
    service_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return update_service_review(service_id, "approved", "validated", db, admin)


@app.post("/services/{service_id}/review/reject", response_model=ServiceRead)
def reject_service_review(
    service_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return update_service_review(service_id, "rejected", "rejected", db, admin)


@app.post("/services/{service_id}/review/reopen", response_model=ServiceRead)
def reopen_service_review(
    service_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return update_service_review(service_id, "pending_review", "pending_review", db, admin)


@app.get("/services/{service_id}", response_model=ServiceRead)
def get_service(
    service_id: str,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    service = db.query(Service).filter(Service.id == service_id).first()

    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    if service.lifecycle_status == "archived" and (
        not user or not can_manage_service(user, service.owner_node)
    ):
        raise HTTPException(status_code=404, detail="Service not found")
    return service


def get_manageable_service(service_id: str, db: Session, user: User) -> Service:
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    if not can_manage_service(user, service.owner_node):
        raise HTTPException(status_code=403, detail="You can only manage services owned by your node")
    return service


@app.put("/services/{service_id}/technical-metadata", response_model=ServiceRead)
def update_service_technical_metadata(
    service_id: str,
    payload: ServiceTechnicalMetadataUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_service_publisher),
):
    service = get_manageable_service(service_id, db, user)
    values = payload.model_dump()
    required_fields = (
        "internal_host",
        "internal_port",
        "health_path",
        "operation_name",
        "input_message_name",
        "output_message_name",
        "proto_uri",
    )
    for field in required_fields:
        values[field] = (values.get(field) or "").strip()
        if not values[field]:
            raise HTTPException(status_code=422, detail=f"{field} is required")
    if values.get("contract_uri") is not None:
        values["contract_uri"] = values["contract_uri"].strip() or None

    runtime_probe = type(
        "RuntimeAddress",
        (),
        {
            "internal_host": values["internal_host"],
            "internal_port": values["internal_port"],
            "health_path": values["health_path"],
        },
    )()
    _, address_error = build_runtime_health_url(runtime_probe)
    if address_error:
        raise HTTPException(status_code=422, detail=address_error)

    changes = {}
    for field, value in values.items():
        old_value = getattr(service, field)
        if old_value != value:
            changes[field] = {"before": old_value, "after": value}
            setattr(service, field, value)

    if changes:
        invalidate_runtime_verification(
            service,
            "Runtime or interface metadata changed; run verification again before execution.",
        )
        touch_updated_at(service)
        record_audit_event(
            db,
            user,
            "service.technical_metadata_updated",
            "service",
            service.id,
            {"changes": changes, "verification_invalidated": True},
        )
        db.commit()
        db.refresh(service)
    return service


@app.post(
    "/services/{service_id}/runtime/verify",
    response_model=RuntimeVerificationRead,
)
def verify_service_runtime(
    service_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_service_publisher),
):
    service = get_manageable_service(service_id, db, user)
    result = check_service_runtime(service)
    evidence = store_runtime_verification(service, result)
    record_audit_event(
        db,
        user,
        "service.runtime_verified" if result["status"] == "ready" else "service.runtime_verification_failed",
        "service",
        service.id,
        {
            "runtime_url": result.get("runtime_url"),
            "http_status": result.get("http_status"),
            "failure_reason": result.get("failure_reason"),
        },
    )
    db.commit()
    return evidence


@app.put("/services/{service_id}/activate", response_model=ServiceRead)
def activate_service(
    service_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_service_publisher),
):
    service = get_manageable_service(service_id, db, user)

    service.lifecycle_status = "active"
    touch_updated_at(service)

    record_audit_event(db, user, "service.activated", "service", service.id)
    db.commit()
    db.refresh(service)

    return service


@app.put("/services/{service_id}/deprecate", response_model=ServiceRead)
def deprecate_service(
    service_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_service_publisher),
):
    service = get_manageable_service(service_id, db, user)

    service.lifecycle_status = "deprecated"
    touch_updated_at(service)

    record_audit_event(db, user, "service.deprecated", "service", service.id)
    db.commit()
    db.refresh(service)

    return service


@app.put("/services/{service_id}/archive", response_model=ServiceRead)
def archive_service(
    service_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_service_publisher),
):
    service = get_manageable_service(service_id, db, user)

    service.lifecycle_status = "archived"
    touch_updated_at(service)

    record_audit_event(db, user, "service.archived", "service", service.id)
    db.commit()
    db.refresh(service)

    return service


@app.put("/services/{service_id}/restore", response_model=ServiceRead)
def restore_service(
    service_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_service_publisher),
):
    service = get_manageable_service(service_id, db, user)

    service.lifecycle_status = "active"
    touch_updated_at(service)

    record_audit_event(db, user, "service.restored", "service", service.id)
    db.commit()
    db.refresh(service)

    return service


# ---------------------------------------------------------------------
# Workflow / Orchestrator
# ---------------------------------------------------------------------

@app.post("/workflows/compile")
def compile_workflow(
    workflow: WorkflowSubmitRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return compile_to_wp3_payload(workflow, db)


@app.post("/workflows/runtime-preflight")
def runtime_preflight_endpoint(
    workflow: WorkflowSubmitRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return run_runtime_preflight(workflow.nodes, db)


@app.post("/workflows/submit-to-orchestrator")
def submit_workflow_to_orchestrator_endpoint(
    workflow: WorkflowSubmitRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if workflow.solution_id:
        solution = db.query(Solution).filter(Solution.id == workflow.solution_id).first()

        if not solution:
            raise HTTPException(status_code=404, detail="Solution not found")

        if not can_manage_owned_record(user, solution.created_by_user_id):
            raise HTTPException(status_code=403, detail="You can only deploy your own solutions")

        if solution.status == "archived":
            raise HTTPException(
                status_code=400,
                detail="Archived solutions cannot be submitted to the orchestrator.",
            )

    preflight = run_runtime_preflight(workflow.nodes, db)

    if preflight["status"] == "blocked":
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Deployment readiness is blocked. Resolve the reported service issues before confirming deployment.",
                "preflight": preflight,
            },
        )

    compiled_payload = compile_to_wp3_payload(workflow, db)

    orchestrator_payload = {
        "blueprint": compiled_payload["blueprint"],
        "dockerinfo": compiled_payload["dockerinfo"],
    }

    if "inputs" in compiled_payload:
        orchestrator_payload["inputs"] = compiled_payload["inputs"]

    if "services_api_key" in compiled_payload:
        orchestrator_payload["services_api_key"] = compiled_payload["services_api_key"]

    orchestrator_result = submit_to_orchestrator(orchestrator_payload)

    if isinstance(orchestrator_result, dict):
        orchestrator_result["solution_studio_metadata"] = compiled_payload.get(
            "solution_studio_metadata"
        )

    return orchestrator_result




@app.post("/workflows/validate")
def validate_workflow(_: User = Depends(get_current_user)):
    return {
        "valid": True,
        "message": "Workflow validation placeholder. Compatibility rules will be added in the next milestone.",
    }


@app.post("/workflows/submit")
def submit_workflow(_: User = Depends(get_current_user)):
    return {
        "workflow_id": "demo-workflow-001",
        "status": "submitted",
        "message": "Submission placeholder. Orchestrator adapter integration comes later.",
    }


@app.get("/workflows/{workflow_id}")
def get_workflow(workflow_id: str, _: User = Depends(get_current_user)):
    return {"workflow_id": workflow_id, "status": "running"}


@app.get("/workflows/{workflow_id}/tasks")
def get_tasks(workflow_id: str, _: User = Depends(get_current_user)):
    return {
        "workflow_id": workflow_id,
        "tasks": [
            {"id": "task-1", "name": "Load input reference", "status": "completed"},
            {"id": "task-2", "name": "Execute AI service", "status": "running"},
        ],
    }


@app.get("/orchestrator/workflows/{workflow_id}")
def orchestrator_workflow_status(
    workflow_id: str,
    _: User = Depends(get_current_user),
):
    return get_workflow_status(workflow_id)


@app.get("/orchestrator/workflows/{workflow_id}/tasks")
def orchestrator_workflow_tasks(
    workflow_id: str,
    _: User = Depends(get_current_user),
):
    return get_workflow_tasks(workflow_id)


# ---------------------------------------------------------------------
# Solutions
# ---------------------------------------------------------------------

@app.post("/solutions", response_model=SolutionRead)
def create_solution(
    payload: SolutionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    solution = Solution(
        id=str(uuid4()),
        name=payload.name,
        description=payload.description,
        nodes=payload.nodes,
        edges=payload.edges,
        status=payload.status,
        created_by_user_id=user.id,
    )

    db.add(solution)
    record_audit_event(db, user, "solution.created", "solution", solution.id)
    db.commit()
    db.refresh(solution)

    return solution


@app.get("/solutions", response_model=list[SolutionRead])
def list_solutions(
    include_archived: bool = False,
    archived_only: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Solution)
    if user.role != "platform_admin":
        query = query.filter(Solution.created_by_user_id == user.id)

    if archived_only:
        query = query.filter(Solution.status == "archived")
    elif not include_archived:
        query = query.filter(Solution.status != "archived")

    return query.order_by(Solution.updated_at.desc()).all()


@app.get("/solutions/summary")
def list_solution_summaries(
    include_archived: bool = False,
    archived_only: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Solution)
    if user.role != "platform_admin":
        query = query.filter(Solution.created_by_user_id == user.id)

    if archived_only:
        query = query.filter(Solution.status == "archived")
    elif not include_archived:
        query = query.filter(Solution.status != "archived")

    solutions = query.order_by(Solution.updated_at.desc()).all()

    summaries = []

    for solution in solutions:
        deployments = (
            db.query(Deployment)
            .filter(
                Deployment.solution_id == solution.id,
                Deployment.is_archived == False,
            )
            .order_by(Deployment.created_at.desc())
            .all()
        )

        latest_deployment = deployments[0] if deployments else None

        completed_count = len(
            [deployment for deployment in deployments if deployment.status == "completed"]
        )
        failed_count = len(
            [deployment for deployment in deployments if deployment.status == "failed"]
        )
        running_count = len(
            [deployment for deployment in deployments if deployment.status == "running"]
        )

        service_count = len(
            [
                node
                for node in (solution.nodes or [])
                if str(node.get("id", "")).startswith("service-")
            ]
        )

        summaries.append(
            {
                "id": solution.id,
                "name": solution.name,
                "description": solution.description,
                "status": solution.status,
                "services_count": service_count,
                "connections_count": len(solution.edges or []),
                "deployments_count": len(deployments),
                "completed_deployments_count": completed_count,
                "failed_deployments_count": failed_count,
                "running_deployments_count": running_count,
                "latest_workflow_id": latest_deployment.workflow_id
                if latest_deployment
                else None,
                "latest_deployment_status": latest_deployment.status
                if latest_deployment
                else None,
                "latest_deployment_created_at": latest_deployment.created_at
                if latest_deployment
                else None,
                "created_at": solution.created_at,
                "updated_at": solution.updated_at,
                "created_by_user_id": solution.created_by_user_id,
            }
        )

    return summaries


@app.get("/solutions/{solution_id}/workspace", response_model=SolutionWithDeploymentsRead)
def get_solution_workspace(
    solution_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    solution = db.query(Solution).filter(Solution.id == solution_id).first()

    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")
    if not can_manage_owned_record(user, solution.created_by_user_id):
        raise HTTPException(status_code=403, detail="You can only access your own solutions")

    deployments = (
        db.query(Deployment)
        .filter(
            Deployment.solution_id == solution.id,
            Deployment.is_archived == False,
        )
        .order_by(Deployment.created_at.desc())
        .all()
    )

    return {
        "id": solution.id,
        "name": solution.name,
        "description": solution.description,
        "nodes": solution.nodes,
        "edges": solution.edges,
        "status": solution.status,
        "created_at": solution.created_at,
        "updated_at": solution.updated_at,
        "created_by_user_id": solution.created_by_user_id,
        "deployments": deployments,
    }


@app.get("/solutions/{solution_id}", response_model=SolutionRead)
def get_solution(
    solution_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    solution = db.query(Solution).filter(Solution.id == solution_id).first()

    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")
    if not can_manage_owned_record(user, solution.created_by_user_id):
        raise HTTPException(status_code=403, detail="You can only access your own solutions")

    return solution


@app.put("/solutions/{solution_id}", response_model=SolutionRead)
def update_solution(
    solution_id: str,
    payload: SolutionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    solution = db.query(Solution).filter(Solution.id == solution_id).first()

    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")
    if not can_manage_owned_record(user, solution.created_by_user_id):
        raise HTTPException(status_code=403, detail="You can only modify your own solutions")

    if solution.status == "archived":
        raise HTTPException(
            status_code=400,
            detail="Archived solutions cannot be edited. Restore the solution first.",
        )

    if payload.name is not None:
        solution.name = payload.name
    if payload.description is not None:
        solution.description = payload.description
    if payload.nodes is not None:
        solution.nodes = payload.nodes
    if payload.edges is not None:
        solution.edges = payload.edges
    if payload.status is not None:
        solution.status = payload.status

    solution.updated_at = datetime.utcnow()

    record_audit_event(db, user, "solution.updated", "solution", solution.id)
    db.commit()
    db.refresh(solution)

    return solution


@app.put("/solutions/{solution_id}/archive", response_model=SolutionRead)
def archive_solution(
    solution_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    solution = db.query(Solution).filter(Solution.id == solution_id).first()

    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")
    if not can_manage_owned_record(user, solution.created_by_user_id):
        raise HTTPException(status_code=403, detail="You can only archive your own solutions")

    solution.status = "archived"
    solution.updated_at = datetime.utcnow()

    record_audit_event(db, user, "solution.archived", "solution", solution.id)
    db.commit()
    db.refresh(solution)

    return solution


@app.put("/solutions/{solution_id}/restore", response_model=SolutionRead)
def restore_solution(
    solution_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    solution = db.query(Solution).filter(Solution.id == solution_id).first()

    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")
    if not can_manage_owned_record(user, solution.created_by_user_id):
        raise HTTPException(status_code=403, detail="You can only restore your own solutions")

    solution.status = "draft"
    solution.updated_at = datetime.utcnow()

    record_audit_event(db, user, "solution.restored", "solution", solution.id)
    db.commit()
    db.refresh(solution)

    return solution


# ---------------------------------------------------------------------
# Deployments
# ---------------------------------------------------------------------

@app.get("/deployments", response_model=list[DeploymentRead])
def list_deployments(
    include_archived: bool = False,
    archived_only: bool = False,
    solution_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Deployment)
    if user.role != "platform_admin":
        query = query.filter(Deployment.created_by_user_id == user.id)

    if solution_id:
        query = query.filter(Deployment.solution_id == solution_id)

    if archived_only:
        query = query.filter(Deployment.is_archived == True)
    elif not include_archived:
        query = query.filter(Deployment.is_archived == False)

    return query.order_by(Deployment.created_at.desc()).all()


@app.post("/deployments/sync-statuses")
def sync_deployment_statuses(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Deployment)
    if user.role != "platform_admin":
        query = query.filter(Deployment.created_by_user_id == user.id)
    deployments = query.order_by(Deployment.created_at.desc()).all()

    summary = {
        "total": len(deployments),
        "updated": 0,
        "unchanged": 0,
        "failed": 0,
        "items": [],
    }

    for deployment in deployments:
        try:
            workflow = get_workflow_status(deployment.workflow_id)
            latest_status = workflow.get("status")

            if not latest_status:
                summary["failed"] += 1
                summary["items"].append(
                    {
                        "workflow_id": deployment.workflow_id,
                        "deployment_id": deployment.id,
                        "status": deployment.status,
                        "sync_status": "failed",
                        "message": "Orchestrator response did not include a status.",
                    }
                )
                continue

            if deployment.status != latest_status:
                old_status = deployment.status
                deployment.status = latest_status
                deployment.updated_at = datetime.utcnow()

                summary["updated"] += 1
                summary["items"].append(
                    {
                        "workflow_id": deployment.workflow_id,
                        "deployment_id": deployment.id,
                        "old_status": old_status,
                        "new_status": latest_status,
                        "sync_status": "updated",
                    }
                )
            else:
                summary["unchanged"] += 1
                summary["items"].append(
                    {
                        "workflow_id": deployment.workflow_id,
                        "deployment_id": deployment.id,
                        "status": deployment.status,
                        "sync_status": "unchanged",
                    }
                )

        except Exception as exc:
            summary["failed"] += 1
            summary["items"].append(
                {
                    "workflow_id": deployment.workflow_id,
                    "deployment_id": deployment.id,
                    "status": deployment.status,
                    "sync_status": "failed",
                    "message": str(exc),
                }
            )

    db.commit()

    return summary


@app.put("/deployments/{deployment_id}/archive", response_model=DeploymentRead)
def archive_deployment(
    deployment_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    if not can_manage_owned_record(user, deployment.created_by_user_id):
        raise HTTPException(status_code=403, detail="You can only archive your own deployments")

    deployment.is_archived = True
    deployment.updated_at = datetime.utcnow()

    record_audit_event(db, user, "deployment.archived", "deployment", deployment.id)
    db.commit()
    db.refresh(deployment)

    return deployment


@app.put("/deployments/{deployment_id}/restore", response_model=DeploymentRead)
def restore_deployment(
    deployment_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    if not can_manage_owned_record(user, deployment.created_by_user_id):
        raise HTTPException(status_code=403, detail="You can only restore your own deployments")

    deployment.is_archived = False
    deployment.updated_at = datetime.utcnow()

    record_audit_event(db, user, "deployment.restored", "deployment", deployment.id)
    db.commit()
    db.refresh(deployment)

    return deployment


@app.get("/deployments/by-workflow/{workflow_id}", response_model=DeploymentRead)
def get_deployment_by_workflow_id(
    workflow_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    deployment = (
        db.query(Deployment)
        .filter(Deployment.workflow_id == workflow_id)
        .first()
    )

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    if not can_manage_owned_record(user, deployment.created_by_user_id):
        raise HTTPException(status_code=403, detail="You can only access your own deployments")

    return deployment


@app.get("/deployments/{deployment_id}", response_model=DeploymentRead)
def get_deployment(
    deployment_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    if not can_manage_owned_record(user, deployment.created_by_user_id):
        raise HTTPException(status_code=403, detail="You can only access your own deployments")

    return deployment


@app.post("/deployments", response_model=DeploymentRead)
def create_deployment(
    deployment: DeploymentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if deployment.solution_id:
        solution = db.query(Solution).filter(Solution.id == deployment.solution_id).first()

        if not solution:
            raise HTTPException(status_code=404, detail="Solution not found")
        if not can_manage_owned_record(user, solution.created_by_user_id):
            raise HTTPException(status_code=403, detail="You can only deploy your own solutions")

        if solution.status == "archived":
            raise HTTPException(
                status_code=400,
                detail="Archived solutions cannot receive new deployments.",
            )

    existing = (
        db.query(Deployment)
        .filter(Deployment.workflow_id == deployment.workflow_id)
        .first()
    )

    if existing:
        if not can_manage_owned_record(user, existing.created_by_user_id):
            raise HTTPException(status_code=403, detail="Deployment belongs to another user")
        return existing

    db_deployment = Deployment(
        id=str(uuid4()),
        workflow_id=deployment.workflow_id,
        solution_id=deployment.solution_id,
        name=deployment.name,
        status=deployment.status,
        is_archived=False,
        created_by_user_id=user.id,
    )

    db.add(db_deployment)
    record_audit_event(db, user, "deployment.created", "deployment", db_deployment.id)
    db.commit()
    db.refresh(db_deployment)

    return db_deployment


@app.put("/deployments/{deployment_id}", response_model=DeploymentRead)
def update_deployment(
    deployment_id: str,
    payload: DeploymentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    if not can_manage_owned_record(user, deployment.created_by_user_id):
        raise HTTPException(status_code=403, detail="You can only update your own deployments")

    if payload.status is not None:
        deployment.status = payload.status

    deployment.updated_at = datetime.utcnow()

    record_audit_event(db, user, "deployment.updated", "deployment", deployment.id)
    db.commit()
    db.refresh(deployment)

    return deployment


# ---------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------

def seed_services(db: Session):
    examples = [
        Service(
            id="svc-pt-input-provider",
            name="PT Input Provider",
            provider="Portuguese Node",
            category="File-Based Energy Pipeline",
            status="validated",
            lifecycle_status="active",
            version="1.0.0",
            description="Provides configuration input for the Portuguese file-based energy pipeline.",
            input_type="Workflow Start",
            output_type="Configuration DataReference",
            trust_badge="Validated",
            container_name="input-provider",
            image="input-provider:latest",
            proto_uri="input_provider.proto",
            node_type="MLModel",
            operation_name="GetConfiguration",
            input_message_name="Request",
            output_message_name="Response",
            internal_host="input-provider",
            internal_port="8080",
        ),
        Service(
            id="svc-pt-data-generator",
            name="PT Data Generator",
            provider="Portuguese Node",
            category="File-Based Energy Pipeline",
            status="validated",
            lifecycle_status="active",
            version="1.0.0",
            description="Generates energy data from pipeline configuration input.",
            input_type="Configuration DataReference",
            output_type="Energy Dataset DataReference",
            trust_badge="Validated",
            container_name="data-generator",
            image="data-generator:latest",
            proto_uri="data_generator.proto",
            node_type="MLModel",
            operation_name="GenerateData",
            input_message_name="Request",
            output_message_name="Response",
            internal_host="data-generator",
            internal_port="8080",
        ),
        Service(
            id="svc-pt-data-analyzer",
            name="PT Data Analyzer",
            provider="Portuguese Node",
            category="File-Based Energy Pipeline",
            status="validated",
            lifecycle_status="active",
            version="1.0.0",
            description="Analyzes generated energy data and produces analysis results.",
            input_type="Energy Dataset DataReference",
            output_type="Analysis DataReference",
            trust_badge="Validated",
            container_name="data-analyzer",
            image="data-analyzer:latest",
            proto_uri="data_analyzer.proto",
            node_type="MLModel",
            operation_name="AnalyzeData",
            input_message_name="Request",
            output_message_name="Response",
            internal_host="data-analyzer",
            internal_port="8080",
        ),
        Service(
            id="svc-pt-report-generator",
            name="PT Report Generator",
            provider="Portuguese Node",
            category="File-Based Energy Pipeline",
            status="validated",
            lifecycle_status="active",
            version="1.0.0",
            description="Generates final reports from analysis output.",
            input_type="Analysis DataReference",
            output_type="Report DataReference",
            trust_badge="Validated",
            container_name="report-generator",
            image="report-generator:latest",
            proto_uri="report_generator.proto",
            node_type="MLModel",
            operation_name="GenerateReport",
            input_message_name="Request",
            output_message_name="Response",
            internal_host="report-generator",
            internal_port="8080",
        ),
    ]

    for service in examples:
        db.merge(service)

    db.commit()
