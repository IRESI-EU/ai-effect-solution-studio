from datetime import datetime
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.db import Base, engine, get_db
from app.models.deployment import Deployment
from app.models.service import Service
from app.models.solution import Solution
from app.schemas.data_reference import DataReferencePreviewRequest
from app.schemas.deployment import (
    DeploymentCreate,
    DeploymentRead,
    DeploymentUpdate,
)
from app.schemas.service import ServiceCreate, ServiceRead
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
from app.services.workflow_compiler import compile_to_wp3_payload
from app.services.wp3_importer import import_wp3_package
from app.schemas.service_import import (
    ServiceImportManualConfirmRequest,
    ServiceImportManualPreviewRequest,
    ServiceImportPreviewRequest,
    ServiceImportPreviewResponse,
)
from app.services.service_manifest_importer import normalize_manifest, preview_service_manifest


Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI-EFFECT Solution Studio API", version="0.1.0")

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


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/admin/import/wp3-package")
def admin_import_wp3_package(
    payload: WP3ImportRequest,
    db: Session = Depends(get_db),
):
    return import_wp3_package(payload, db)


@app.post("/data-references/preview")
def preview_data_reference_endpoint(payload: DataReferencePreviewRequest):
    return preview_data_reference(payload.protocol, payload.uri)


# ---------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------

@app.get("/services", response_model=list[ServiceRead])
def list_services(
    include_archived: bool = False,
    archived_only: bool = False,
    db: Session = Depends(get_db),
):
    services_exist = db.query(Service).first()

    if not services_exist:
        seed_services(db)

    query = db.query(Service)

    if archived_only:
        query = query.filter(Service.lifecycle_status == "archived")
    elif not include_archived:
        query = query.filter(Service.lifecycle_status != "archived")

    return query.order_by(Service.name.asc()).all()


@app.post("/services", response_model=ServiceRead)
def create_service(payload: ServiceCreate, db: Session = Depends(get_db)):
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
    )

    db.add(service)
    db.commit()
    db.refresh(service)

    return service
@app.post("/services/import/preview", response_model=ServiceImportPreviewResponse)
def preview_service_import(request: ServiceImportPreviewRequest):
    return preview_service_manifest(
        repo_url=request.repo_url,
        branch=request.branch,
        manifest_path=request.manifest_path,
    )

@app.post("/services/import/preview-manual", response_model=ServiceImportPreviewResponse)
def preview_manual_service_import(request: ServiceImportManualPreviewRequest):
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
):
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
        container_name=imported.container_name,
        image=imported.image or "",
        proto_uri=imported.proto_uri or imported.contract_uri or request.manifest_path,
        node_type="MLModel",
        operation_name=imported.operation_name,
        input_message_name=imported.input_message_name,
        output_message_name=imported.output_message_name,
        input_type=imported.input_type,
        output_type=imported.output_type,
        internal_host=imported.container_name,
        internal_port=imported.internal_port,
    )

    db.add(service)
    db.commit()
    db.refresh(service)

    return service

@app.get("/services/{service_id}", response_model=ServiceRead)
def get_service(service_id: str, db: Session = Depends(get_db)):
    service = db.query(Service).filter(Service.id == service_id).first()

    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    return service


@app.put("/services/{service_id}/activate", response_model=ServiceRead)
def activate_service(service_id: str, db: Session = Depends(get_db)):
    service = db.query(Service).filter(Service.id == service_id).first()

    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    service.lifecycle_status = "active"
    touch_updated_at(service)

    db.commit()
    db.refresh(service)

    return service


@app.put("/services/{service_id}/deprecate", response_model=ServiceRead)
def deprecate_service(service_id: str, db: Session = Depends(get_db)):
    service = db.query(Service).filter(Service.id == service_id).first()

    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    service.lifecycle_status = "deprecated"
    touch_updated_at(service)

    db.commit()
    db.refresh(service)

    return service


@app.put("/services/{service_id}/archive", response_model=ServiceRead)
def archive_service(service_id: str, db: Session = Depends(get_db)):
    service = db.query(Service).filter(Service.id == service_id).first()

    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    service.lifecycle_status = "archived"
    touch_updated_at(service)

    db.commit()
    db.refresh(service)

    return service


@app.put("/services/{service_id}/restore", response_model=ServiceRead)
def restore_service(service_id: str, db: Session = Depends(get_db)):
    service = db.query(Service).filter(Service.id == service_id).first()

    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    service.lifecycle_status = "active"
    touch_updated_at(service)

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
):
    return compile_to_wp3_payload(workflow, db)


@app.post("/workflows/submit-to-orchestrator")
def submit_workflow_to_orchestrator_endpoint(
    workflow: WorkflowSubmitRequest,
    db: Session = Depends(get_db),
):
    if workflow.solution_id:
        solution = db.query(Solution).filter(Solution.id == workflow.solution_id).first()

        if not solution:
            raise HTTPException(status_code=404, detail="Solution not found")

        if solution.status == "archived":
            raise HTTPException(
                status_code=400,
                detail="Archived solutions cannot be submitted to the orchestrator.",
            )

    for node in workflow.nodes:
        if not node.service_id:
            continue

        service = db.query(Service).filter(Service.id == node.service_id).first()

        if not service:
            raise HTTPException(
                status_code=404,
                detail=f"Service not found: {node.service_id}",
            )

        if getattr(service, "lifecycle_status", "active") == "archived":
            raise HTTPException(
                status_code=400,
                detail=f"Archived service cannot be submitted: {service.name}",
            )

    payload = compile_to_wp3_payload(workflow, db)
    return submit_to_orchestrator(payload)


@app.post("/workflows/validate")
def validate_workflow():
    return {
        "valid": True,
        "message": "Workflow validation placeholder. Compatibility rules will be added in the next milestone.",
    }


@app.post("/workflows/submit")
def submit_workflow():
    return {
        "workflow_id": "demo-workflow-001",
        "status": "submitted",
        "message": "Submission placeholder. Orchestrator adapter integration comes later.",
    }


@app.get("/workflows/{workflow_id}")
def get_workflow(workflow_id: str):
    return {"workflow_id": workflow_id, "status": "running"}


@app.get("/workflows/{workflow_id}/tasks")
def get_tasks(workflow_id: str):
    return {
        "workflow_id": workflow_id,
        "tasks": [
            {"id": "task-1", "name": "Load input reference", "status": "completed"},
            {"id": "task-2", "name": "Execute AI service", "status": "running"},
        ],
    }


@app.get("/orchestrator/workflows/{workflow_id}")
def orchestrator_workflow_status(workflow_id: str):
    return get_workflow_status(workflow_id)


@app.get("/orchestrator/workflows/{workflow_id}/tasks")
def orchestrator_workflow_tasks(workflow_id: str):
    return get_workflow_tasks(workflow_id)


# ---------------------------------------------------------------------
# Solutions
# ---------------------------------------------------------------------

@app.post("/solutions", response_model=SolutionRead)
def create_solution(payload: SolutionCreate, db: Session = Depends(get_db)):
    solution = Solution(
        id=str(uuid4()),
        name=payload.name,
        description=payload.description,
        nodes=payload.nodes,
        edges=payload.edges,
        status=payload.status,
    )

    db.add(solution)
    db.commit()
    db.refresh(solution)

    return solution


@app.get("/solutions", response_model=list[SolutionRead])
def list_solutions(
    include_archived: bool = False,
    archived_only: bool = False,
    db: Session = Depends(get_db),
):
    query = db.query(Solution)

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
):
    query = db.query(Solution)

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
            }
        )

    return summaries


@app.get("/solutions/{solution_id}/workspace", response_model=SolutionWithDeploymentsRead)
def get_solution_workspace(solution_id: str, db: Session = Depends(get_db)):
    solution = db.query(Solution).filter(Solution.id == solution_id).first()

    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")

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
        "deployments": deployments,
    }


@app.get("/solutions/{solution_id}", response_model=SolutionRead)
def get_solution(solution_id: str, db: Session = Depends(get_db)):
    solution = db.query(Solution).filter(Solution.id == solution_id).first()

    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")

    return solution


@app.put("/solutions/{solution_id}", response_model=SolutionRead)
def update_solution(
    solution_id: str,
    payload: SolutionUpdate,
    db: Session = Depends(get_db),
):
    solution = db.query(Solution).filter(Solution.id == solution_id).first()

    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")

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

    db.commit()
    db.refresh(solution)

    return solution


@app.put("/solutions/{solution_id}/archive", response_model=SolutionRead)
def archive_solution(solution_id: str, db: Session = Depends(get_db)):
    solution = db.query(Solution).filter(Solution.id == solution_id).first()

    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")

    solution.status = "archived"
    solution.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(solution)

    return solution


@app.put("/solutions/{solution_id}/restore", response_model=SolutionRead)
def restore_solution(solution_id: str, db: Session = Depends(get_db)):
    solution = db.query(Solution).filter(Solution.id == solution_id).first()

    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")

    solution.status = "draft"
    solution.updated_at = datetime.utcnow()

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
):
    query = db.query(Deployment)

    if solution_id:
        query = query.filter(Deployment.solution_id == solution_id)

    if archived_only:
        query = query.filter(Deployment.is_archived == True)
    elif not include_archived:
        query = query.filter(Deployment.is_archived == False)

    return query.order_by(Deployment.created_at.desc()).all()


@app.post("/deployments/sync-statuses")
def sync_deployment_statuses(db: Session = Depends(get_db)):
    deployments = db.query(Deployment).order_by(Deployment.created_at.desc()).all()

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
def archive_deployment(deployment_id: str, db: Session = Depends(get_db)):
    deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    deployment.is_archived = True
    deployment.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(deployment)

    return deployment


@app.put("/deployments/{deployment_id}/restore", response_model=DeploymentRead)
def restore_deployment(deployment_id: str, db: Session = Depends(get_db)):
    deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    deployment.is_archived = False
    deployment.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(deployment)

    return deployment


@app.get("/deployments/by-workflow/{workflow_id}", response_model=DeploymentRead)
def get_deployment_by_workflow_id(
    workflow_id: str,
    db: Session = Depends(get_db),
):
    deployment = (
        db.query(Deployment)
        .filter(Deployment.workflow_id == workflow_id)
        .first()
    )

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    return deployment


@app.get("/deployments/{deployment_id}", response_model=DeploymentRead)
def get_deployment(deployment_id: str, db: Session = Depends(get_db)):
    deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    return deployment


@app.post("/deployments", response_model=DeploymentRead)
def create_deployment(
    deployment: DeploymentCreate,
    db: Session = Depends(get_db),
):
    if deployment.solution_id:
        solution = db.query(Solution).filter(Solution.id == deployment.solution_id).first()

        if not solution:
            raise HTTPException(status_code=404, detail="Solution not found")

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
        return existing

    db_deployment = Deployment(
        id=str(uuid4()),
        workflow_id=deployment.workflow_id,
        solution_id=deployment.solution_id,
        name=deployment.name,
        status=deployment.status,
        is_archived=False,
    )

    db.add(db_deployment)
    db.commit()
    db.refresh(db_deployment)

    return db_deployment


@app.put("/deployments/{deployment_id}", response_model=DeploymentRead)
def update_deployment(
    deployment_id: str,
    payload: DeploymentUpdate,
    db: Session = Depends(get_db),
):
    deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    if payload.status is not None:
        deployment.status = payload.status

    deployment.updated_at = datetime.utcnow()

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