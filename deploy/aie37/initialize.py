"""One-time import into ONLY the empty, isolated qualification database.

Mirrors two approved Dutch operations, using their recorded catalogue provenance.
No earlier account, catalogue, database, allowance or profile is changed.
"""
import json
from pathlib import Path
import secrets

from app.main import app
from app.db import SessionLocal
from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User
from app.models.service import Service
from app.schemas.operation_contract import OperationContractCreate
from app.services.operation_contract_registry import create_contract, activate_contract
from app.services.local_dutch_capture import qualification_enabled

assert qualification_enabled()
contracts = json.loads(Path("/qualification/contracts.json").read_text())
source = json.loads(Path("/source-services.json").read_text())
assert len(source) == 2 and {s["operation_name"] for s in source} == set(contracts)
with SessionLocal() as db:
    assert db.query(User).count() == 0 and db.query(Service).count() == 0, "Existing profiles must never be reinitialized"
    password = secrets.token_urlsafe(24)
    db.add(User(id="aie37-designer", email="aie37-designer@example.test", display_name="Dutch workflow qualification reviewer",
        password_hash=hash_password(password), role="solution_designer", status="active"))
    db.add(User(id="aie37-node-owner", email="aie37-node-owner@example.test", display_name="Isolated Dutch catalogue owner mirror",
        password_hash=hash_password(secrets.token_urlsafe(32)), role="node_manager", node="NL", status="active"))
    db.commit()
    for item in source:
        method = item["operation_name"]
        assert item["status"] in {"approved", "validated"}
        role = "synth" if method == "ConfigureAndSynthesize" else "benchmark"
        values = {k: v for k, v in item.items() if k in Service.__table__.columns.keys()}
        values.update(id="aie37-" + role, created_by_user_id="aie37-node-owner", owner_node="NL",
            name="Generate synthetic power grid" if role == "synth" else "Benchmark generated grid",
            internal_host="seed-" + role, internal_port="8080", health_path="/health",
            container_name="grid_synth_service" if role == "synth" else "benchmark-runner",
            image="ai-effect-aie37-" + role + ":qualification-v1",
            repository_url="https://github.com/AI-EFFECT/ai-effect-wp3",
            repository_branch="ba598b2459f9986dac4e37dcc5d7d3298f25dc3a",
            manifest_path="use-cases/dutch_node/" + ("data_synthesizer" if role == "synth" else "benchmarking"),
            version="dutch-capture-v1", input_type="None" if role == "synth" else "Captured Dutch grid",
            output_type="Captured Dutch grid" if role == "synth" else "Benchmark results")
        db.add(Service(**values))
    db.commit()
    for method, value in contracts.items():
        sid = "aie37-synth" if method == "ConfigureAndSynthesize" else "aie37-benchmark"
        activate_contract(create_contract(sid, OperationContractCreate.model_validate(value), db).id, db)
    Path("/tmp/aie37-reviewer.json").write_text(json.dumps({
        "email": "aie37-designer@example.test", "password": password}), encoding="utf-8")
print("Initialized only the new qualification catalogue. Reviewer credentials are in the private local record.")
