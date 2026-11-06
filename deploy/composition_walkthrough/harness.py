"""Opt-in host-only acceptance harness; never imported by production startup.

Actual portal routes, disposable SQLite, two labelled synthetic operations and
precomputed provider-boundary fixtures. No live AI, readiness or execution.
"""
import argparse
from copy import deepcopy
import inspect
import json
import os
from pathlib import Path
import secrets
import socket
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps/api"))
LABEL = "Offline controls walkthrough: prepared synthetic proposal. No live AI or execution."
PROMPT = "Prepared synthetic controls proposal: generate three test observations and analyze them."
WEB_PORT, API_PORT = 23123, 28187


def configure(profile):
    profile = profile.resolve(strict=True)
    os.environ.update(DATABASE_URL="sqlite:///" + (profile / "walkthrough.sqlite3").as_posix(),
        DESIGN_AI_ENABLED="true", DESIGN_AI_TEMPLATES="{}", OPENAI_API_KEY="", DESIGN_AI_MODEL="",
        DESIGN_AI_ACCEPTANCE_BUDGET_FILE="", DESIGN_AI_ACCEPTANCE_TASK_LIMIT_FILE="",
        BOOTSTRAP_ADMIN_EMAIL="", BOOTSTRAP_ADMIN_PASSWORD="", SECURE_COOKIES="false",
        SESSION_COOKIE_NAME="ai_effect_composition_controls_20261106", ORCHESTRATOR_API_KEY="",
        ORCHESTRATOR_BASE_URL="http://127.0.0.1:9", AIE18_EVIDENCE_ROOT="", AIE37_QUALIFICATION="false",
        LOCAL_DUTCH_AUTO_CAPTURE_ROOT="", LOCAL_DUTCH_CAPTURE_RUNTIME="", LOCAL_DUTCH_EVIDENCE_ROOT="",
        LOCAL_DUTCH_EVIDENCE_SCOPE="", DESIGN_AI_DUTCH_DEMO="false", DESIGN_AI_DEMO_EXECUTION_GRANT_FILE="")
    # Same test-only JSONB compilation used by the portable suite. No production
    # SQLAlchemy types, migrations or database defaults are changed.
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy.ext.compiler import compiles
    @compiles(JSONB, "sqlite")
    def sqlite_jsonb(_type, compiler, **kw):
        return "JSON"


def deny_network():
    original = socket.socket.connect
    def forbidden(*args, **kwargs):
        raise RuntimeError("OFFLINE controls: outbound network prohibited")
    def guarded_connect(self, address):
        # Windows asyncio's authenticated stdlib wake-up socketpair only.
        if inspect.currentframe().f_back.f_code is getattr(socket.socketpair, "__code__", None):
            return original(self, address)
        return forbidden()
    socket.socket.connect = guarded_connect
    socket.socket.connect_ex = forbidden
    socket.create_connection = forbidden


def build_app(profile, *, preparing=False):
    configure(profile)
    from fastapi import Depends, HTTPException
    from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
    import app.main as main
    from app.db import get_db
    from app.dependencies.auth import get_optional_user
    from app.schemas.design_ai import AssistantTurn
    from app.services import catalogue_composition, design_ai_provider, orchestrator_adapter, runtime_preflight

    def prohibited(*args, **kwargs):
        raise HTTPException(403, "OFFLINE controls: readiness, provider network and execution prohibited")
    async def prohibited_provider(*args, **kwargs):
        return prohibited()
    design_ai_provider.AsyncOpenAI = prohibited
    design_ai_provider.OpenAIProvider.respond = prohibited_provider
    for module, names in ((main, ("run_runtime_preflight", "submit_to_orchestrator", "require_binding_transport", "get_workflow_status", "get_workflow_tasks", "check_service_runtime")),
                          (orchestrator_adapter, ("submit_to_orchestrator", "get_workflow_status", "get_workflow_tasks")),
                          (runtime_preflight, ("run_runtime_preflight", "check_service_runtime"))):
        for name in names:
            setattr(module, name, prohibited)

    class PreparedFixture:
        name, mode = LABEL, "test"
        async def respond(self, context):
            if not preparing or context.get("request") != PROMPT or context.get("draft") or context.get("history"):
                raise HTTPException(403, "Prepared fixture only; arbitrary chat is disabled. No model request was made.")
            pairs = context.get("catalogue_discovery", {}).get("operation_pairs", [])
            if len(pairs) != 1:
                raise HTTPException(409, "Expected exactly one validated synthetic pair")
            return AssistantTurn(message=LABEL, template_key=None, expected_revision=None, edits=[],
                discovery={"outcome": "supported_recommendation", "candidate_id": pairs[0]["candidate_id"]},
                composition_settings={"first": [{"name": "count", "value": 3}], "second": []})

    main.app.dependency_overrides[design_ai_provider.get_provider] = lambda: PreparedFixture()

    @main.app.middleware("http")
    async def execution_guard(request, call_next):
        path = request.url.path
        blocked = (path.startswith(("/workflows", "/orchestrator", "/deployments", "/runtimes", "/runtime", "/data-references"))
                   or "execution" in path or "readiness" in path or "runtime" in path
                   or (path == "/design-ai/chat" and not preparing))
        allowed_write = path in {"/auth/login", "/auth/logout"} or path.startswith("/design-ai/drafts") or (preparing and path == "/design-ai/chat")
        if blocked or (request.method not in {"GET", "HEAD", "OPTIONS"} and not allowed_write):
            return JSONResponse({"detail": "OFFLINE controls: this action is disabled; no AI or workflow executed"}, status_code=403)
        return await call_next(request)

    @main.app.get("/offline-controls/{case}", response_class=HTMLResponse)
    def entry(case: str, user=Depends(get_optional_user), db=Depends(get_db)):
        if case not in {"agent", "human"}:
            raise HTTPException(404)
        if user is None:
            return RedirectResponse("/login?next=/api/offline-controls/" + case, status_code=303)
        if user.id != "controls-" + case:
            raise HTTPException(403, "Use the dedicated " + case + " walkthrough account")
        value = json.loads((profile / ("prepared-" + case + ".json")).read_text(encoding="utf-8"))
        record = catalogue_composition.resolve(value["recommendation"]["candidate_id"], db, user)
        if record["revision"] != value["recommendation"]["recommendation_revision"]:
            raise HTTPException(409, "Prepared authority changed; do not reset or silently replace the proposal")
        conversation = {"ownerId": user.id, "draftId": None,
            "messages": [{"role": "assistant", "content": LABEL + " Review the prepared steps and use the explicit controls; chat is disabled."}],
            "activity": value["activity"], "prompt": "", "seedInput": "42", "historyUnavailable": False,
            "recommendation": value["recommendation"]}
        # Only bootstrap the normal application's existing conversation format.
        # No mock Create/Apply/Undo/Save controls and no auth/session override.
        payload = json.dumps(conversation).replace("<", "\\u003c")
        key = json.dumps("design-ai-discovery:" + user.id)
        return HTMLResponse('<!doctype html><meta charset="utf-8"><title>Offline controls walkthrough</title>'
            '<p>' + LABEL + '</p><p>Opening the actual Design with AI application…</p>'
            '<script>localStorage.setItem(' + key + ',JSON.stringify(' + payload + '));location.replace("/design-ai");</script>',
            headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})
    return main.app


def seed(profile):
    from app.core.security import hash_password
    from app.db import SessionLocal
    from app.models.user import User
    from app.models.service import Service
    from app.models.operation_contract import OperationContract
    credentials = {case: {"email": "controls-" + case + "@example.test", "password": secrets.token_urlsafe(24)} for case in ("agent", "human")}
    (profile / "private-credentials.json").write_text(json.dumps(credentials, indent=2), encoding="utf-8")
    slot = {"name": "observations", "semantic_concept": "synthetic test observations", "schema_ref": "urn:offline-controls:observations:1",
        "value_representation": "data_reference", "data_reference_protocols": ["file"], "content_types": ["application/json"], "min_cardinality": 1, "max_cardinality": 1}
    with SessionLocal() as db:
        for case, account in credentials.items():
            db.add(User(id="controls-" + case, email=account["email"], display_name="OFFLINE controls " + case + " reviewer",
                password_hash=hash_password(account["password"]), role="solution_designer", status="active"))
        for index, title in enumerate(("generator", "analyzer")):
            service = Service(id="offline-controls-" + title, name="OFFLINE synthetic observation " + title,
                provider="Synthetic controls fixture; no live service", category="offline-controls", status="approved", lifecycle_status="active",
                description=("Proposes a reference to three synthetic test observations; nothing is generated." if index == 0 else
                    "Would analyze the same upstream observations reference; no analysis is executed."),
                input_type="synthetic observations reference", output_type="synthetic reference", operation_name="OfflineFixture" + str(index),
                container_name="offline-controls-" + title, image="offline-controls:not-a-runtime", proto_uri="offline-controls.proto",
                internal_host="unavailable-offline-service", internal_port="9")
            db.add(service); db.flush()
            definition = {"operation_role": "source" if index == 0 else "analyzer", "binding_transport": "whole-output-v1",
                "inputs": [] if index == 0 else [{**deepcopy(slot), "required": True, "source_requirement": "upstream_operation"}],
                "outputs": [deepcopy(slot)]}
            if index == 0:
                definition["execution_parameters"] = {"schema_version": "1.0", "transport": "http-parameters-v1", "properties": {
                    "count": {"type": "integer", "title": "Synthetic observation count", "description": "Prepared registry-default count, not runtime evidence.",
                              "required": True, "minimum": 1, "maximum": 10, "default": 3}}}
            db.add(OperationContract(id="offline-controls-contract-" + title, service_id=service.id,
                operation_identity="urn:offline-controls:operation:" + title, runtime_operation_name=service.operation_name,
                contract_version="1.0.0", schema_version="1.0", status="active", source_kind="demo", definition=definition))
        db.commit()
    return credentials


def prepare(profile):
    profile.mkdir(parents=True, exist_ok=False)  # Never reset or overwrite a walkthrough.
    app = build_app(profile, preparing=True)
    credentials = seed(profile)
    deny_network()
    from fastapi.testclient import TestClient
    from app.db import SessionLocal
    from app.models.design_ai import DesignDraft
    from app.models.solution import Solution
    with TestClient(app) as client:
        for case, account in credentials.items():
            assert client.post("/auth/login", json=account).status_code == 200
            response = client.post("/design-ai/chat", json={"message": PROMPT})
            assert response.status_code == 200, response.text
            (profile / ("prepared-" + case + ".json")).write_text(json.dumps(response.json(), indent=2), encoding="utf-8")
            client.post("/auth/logout")
    with SessionLocal() as db:
        assert db.query(DesignDraft).count() == db.query(Solution).count() == 0
    print("Prepared two separate owner-bound recommendations; zero drafts, zero saved solutions; no live AI or execution")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "serve"))
    parser.add_argument("--profile", required=True, type=Path)
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.profile.resolve())
    else:
        import uvicorn
        application = build_app(args.profile.resolve(strict=True))
        deny_network()
        uvicorn.run(application, host="127.0.0.1", port=API_PORT, access_log=False)
