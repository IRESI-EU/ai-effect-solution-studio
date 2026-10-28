"""Explicit offline composition harness, separate from normal application behavior.

Reuses an existing loopback PostgreSQL cluster with one new disposable database.
Never starts runtime containers, submits workflows or invokes an SDK/provider.
"""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import secrets
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps/api"))
DATABASE = "design_aie38_offline_20261028"
PROMPT = "Add a benchmark step after the grid generator and use the grid it produces. Keep the generator settings unchanged."


def configure(config):
    os.environ.update(DATABASE_URL=config["database_url"], DESIGN_AI_ENABLED="true",
        DESIGN_AI_TEMPLATES=json.dumps(config["templates"]), OPENAI_API_KEY="", DESIGN_AI_MODEL="",
        DESIGN_AI_ACCEPTANCE_BUDGET_FILE="", DESIGN_AI_ACCEPTANCE_TASK_LIMIT_FILE="",
        BOOTSTRAP_ADMIN_EMAIL="", BOOTSTRAP_ADMIN_PASSWORD="", SESSION_COOKIE_NAME="ai_effect_aie38_offline_session",
        ORCHESTRATOR_BASE_URL="http://127.0.0.1:9", AIE18_EVIDENCE_ROOT="",
        AIE37_QUALIFICATION="false", LOCAL_DUTCH_AUTO_CAPTURE_ROOT="", LOCAL_DUTCH_CAPTURE_RUNTIME="",
        LOCAL_DUTCH_EVIDENCE_ROOT="", LOCAL_DUTCH_EVIDENCE_SCOPE="")


def prepare(profile, source_env):
    import psycopg
    from psycopg import sql
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url
    profile.mkdir(parents=True, exist_ok=False)
    raw = dict(line.split("=", 1) for line in source_env.read_text().splitlines())["DATABASE_URL"]
    source_url = make_url(raw).set(host="127.0.0.1", port=28145)
    assert source_url.database == "design_aie37_qualification"
    engine = create_engine(source_url)
    with engine.connect() as connection:
        connection.execute(text("SET TRANSACTION READ ONLY"))
        services = [dict(r) for r in connection.execute(text("select * from services where id in ('aie37-synth','aie37-benchmark')")).mappings()]
        contracts = [dict(r) for r in connection.execute(text("select * from operation_contracts where service_id in ('aie37-synth','aie37-benchmark') and status='active'")).mappings()]
        source = dict(connection.execute(text("select * from solutions where id='98eadd46-5b58-4517-b706-f2a7b9ed6bc4'")).mappings().one())
    engine.dispose()
    assert len(services) == len(contracts) == 2
    target = source_url.set(database=DATABASE)
    with psycopg.connect(source_url.set(drivername="postgresql", database="postgres").render_as_string(hide_password=False), autocommit=True) as admin:
        assert not admin.execute("select 1 from pg_database where datname=%s", (DATABASE,)).fetchone(), "Existing database must never be reset"
        admin.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0 ENCODING 'UTF8'").format(sql.Identifier(DATABASE)))
    config = {"database_url": target.render_as_string(hide_password=False),
        "templates": {"dutch": {"solution_id": "aie38-one-step-source", "structural_append_only": True}},
        "reviewer": {"email": "aie38-offline@example.test", "password": secrets.token_urlsafe(24)}}
    (profile / "private-config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    configure(config)
    from app.main import app  # noqa: F401
    from app.db import SessionLocal
    from app.core.security import hash_password
    from app.models.user import User
    from app.models.service import Service
    from app.models.operation_contract import OperationContract
    from app.models.solution import Solution
    nodes = [deepcopy(n) for n in source["nodes"] if n["id"] != "benchmark-grid"]
    edges = [deepcopy(e) for e in source["edges"] if e["source"] == "input"]
    terminal = deepcopy(next(e for e in source["edges"] if e["target"] == "output"))
    terminal.update(id="aie38-generator-output", source="generate-grid")
    edges.append(terminal)
    with SessionLocal() as db:
        db.add(User(id="aie38-offline-designer", email=config["reviewer"]["email"], display_name="AIE-38 offline reviewer",
            password_hash=hash_password(config["reviewer"]["password"]), role="solution_designer", status="active"))
        for service in services: db.add(Service(**service))
        db.commit()
        for contract in contracts: db.add(OperationContract(**contract))
        db.add(Solution(id="aie38-one-step-source", name="OFFLINE · grid composition copy", status="draft",
            description="Disposable one-step source; fixture interpretation only; no execution.", nodes=nodes, edges=edges,
            created_by_user_id="aie38-offline-designer", design_metadata={"run_input": deepcopy((source["design_metadata"] or {}).get("run_input"))}))
        db.commit()
    (profile / "source-record.json").write_text(json.dumps({"original_solution": source["id"], "nodes": nodes, "edges": edges}, indent=2), encoding="utf-8")
    print("Prepared one new offline database; existing qualification and execution permission preserved")


def serve(profile):
    configure(json.loads((profile / "private-config.json").read_text()))
    import uvicorn
    from fastapi import HTTPException
    from fastapi.responses import HTMLResponse, JSONResponse
    from app.main import app
    import app.routers.design_ai as router
    from app.services.design_ai_provider import get_provider, OpenAIProvider
    from app.schemas.design_ai import AssistantTurn
    async def forbidden(*args, **kwargs):
        raise AssertionError("OFFLINE: provider SDK prohibited")
    OpenAIProvider.respond = forbidden

    class Fixture:
        name, mode = "OFFLINE structural provider-boundary fixtures", "test"
        async def respond(self, context):
            path = profile / "queued-turn.json"
            if not path.exists():
                raise HTTPException(503, "OFFLINE: no response queued; no model request made")
            queued = json.loads(path.read_text())
            if queued["draft_id"] != context["draft"]["id"] or queued["revision"] != context["draft"]["revision"] or queued["request"] != context["request"] or queued["configuration"] != context["configuration"]:
                raise HTTPException(409, "OFFLINE: queued response does not match this exact draft context/request")
            turn = AssistantTurn.model_validate(queued["turn"])
            path.unlink()  # Single-use explicit boundary response, never a fallback.
            with (profile / "boundary-calls.jsonl").open("a", encoding="utf-8") as log:
                log.write(json.dumps({"context": context, "turn": turn.model_dump()}) + "\n")
            return turn
    app.dependency_overrides[get_provider] = lambda: Fixture()
    router.configured = lambda: True

    @app.middleware("http")
    async def execution_guard(request, call_next):
        path = request.url.path
        if ((path.startswith("/workflows") and path != "/workflows/compile") or path.startswith("/orchestrator")
                or path.startswith("/deployments") or path.startswith("/runtimes")):
            return JSONResponse({"detail": "OFFLINE: runtime access and workflow submission prohibited"}, status_code=403)
        return await call_next(request)

    @app.get("/offline-fixture/narrow", response_class=HTMLResponse)
    def narrow(draft_id: str):
        from uuid import UUID
        identifier = str(UUID(draft_id))
        return ('<!doctype html><meta charset="utf-8"><title>OFFLINE narrow composition review</title>'
            '<style>body{font:15px system-ui;background:#eef0f6;margin:20px}iframe{width:390px;height:844px;border:2px solid #6550a5}</style>'
            '<h1>OFFLINE responsive layout fixture</h1><p>Actual application at 390 × 844 CSS pixels. Fixture responses, no workflow execution. Not physical-device or independent usability evidence.</p>'
            f'<iframe title="Narrow composition application" src="/design-ai?draftId={identifier}"></iframe>')
    uvicorn.run(app, host="127.0.0.1", port=28186, access_log=False)


def queue(profile, draft_id, case):
    configure(json.loads((profile / "private-config.json").read_text()))
    from app.db import SessionLocal
    from app.models.design_ai import DesignDraft
    from app.models.user import User
    from app.services.structural_proposals import context
    with SessionLocal() as db:
        row = db.get(DesignDraft, draft_id)
        assert row.owner_id == "aie38-offline-designer"
        configuration = context(row, db, db.get(User, row.owner_id))
        candidate = configuration["compatible_candidates"][0]
        value = {k: candidate[k] for k in ("local_ref", "service_id", "contract_id", "contract_version", "source_slot", "target_slot")}
        turn = {"message": "OFFLINE FIXTURE: Add the benchmark using the generator's captured_grid. Generator settings stay unchanged. Review the terminal rewiring; no workflow executes.",
            "template_key": None, "expected_revision": row.revision, "edits": [{"kind": "append_bound_operation", "node_id": candidate["source_node_id"], "value": json.dumps(value)}]}
        request = PROMPT
        if case == "ambiguous":
            turn.update(message="OFFLINE FIXTURE: Which generator should supply the benchmark? No design changed.", edits=[])
            request = "Add a benchmark using the grid."
        (profile / "queued-turn.json").write_text(json.dumps({"draft_id": row.id, "revision": row.revision, "request": request, "configuration": configuration, "turn": turn}, indent=2), encoding="utf-8")
        (profile / f"starting-{draft_id}-r{row.revision}.json").write_text(json.dumps({"id": row.id, "revision": row.revision, "design": row.state["design"]}, indent=2), encoding="utf-8")
    print(json.dumps({"queued_fixture": case, "draft_id": draft_id, "revision": row.revision}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "serve", "queue"])
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--source-env", type=Path)
    parser.add_argument("--draft")
    parser.add_argument("--case", choices=["main", "ambiguous"], default="main")
    args = parser.parse_args()
    if args.action == "prepare": prepare(args.profile, args.source_env)
    elif args.action == "serve": serve(args.profile)
    else: queue(args.profile, args.draft, args.case)
