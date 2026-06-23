from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.wp3_import import WP3ImportRequest
from app.services.wp3_importer import import_wp3_package
from app.schemas.data_reference import DataReferencePreviewRequest
from app.services.data_reference_service import preview_data_reference
from datetime import datetime
from app.models.solution import Solution
from app.schemas.solution import SolutionCreate, SolutionRead, SolutionUpdate


from app.db import Base, engine, get_db
from app.models.service import Service
from app.schemas.service import ServiceCreate, ServiceRead
from app.schemas.workflow_submit import WorkflowSubmitRequest
from app.services.workflow_compiler import compile_to_wp3_payload
from app.services.orchestrator_adapter import (
    submit_to_orchestrator,
    get_workflow_status,
    get_workflow_tasks,
)


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

@app.post("/workflows/compile")
def compile_workflow(workflow: WorkflowSubmitRequest):
    return compile_to_wp3_payload(workflow)


@app.post("/workflows/submit-to-orchestrator")
def submit_workflow_to_orchestrator(workflow: WorkflowSubmitRequest):
    payload = compile_to_wp3_payload(workflow)
    return submit_to_orchestrator(payload)



@app.get("/orchestrator/workflows/{workflow_id}")
def orchestrator_workflow_status(workflow_id: str):
    return get_workflow_status(workflow_id)


@app.get("/orchestrator/workflows/{workflow_id}/tasks")
def orchestrator_workflow_tasks(workflow_id: str):
    return get_workflow_tasks(workflow_id)

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

@app.get("/services", response_model=list[ServiceRead])
def list_services(db: Session = Depends(get_db)):
    services = db.query(Service).all()

    if not services:
        seed_services(db)
        services = db.query(Service).all()

    return services


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


@app.get("/services/{service_id}", response_model=ServiceRead)
def get_service(service_id: str, db: Session = Depends(get_db)):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service


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
def list_solutions(db: Session = Depends(get_db)):
    return db.query(Solution).order_by(Solution.updated_at.desc()).all()


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

def seed_services(db: Session):
    examples = [
    Service(
        id="svc-pt-input-provider",
        name="PT Input Provider",
        provider="Portuguese Node",
        category="File-Based Energy Pipeline",
        status="validated",
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