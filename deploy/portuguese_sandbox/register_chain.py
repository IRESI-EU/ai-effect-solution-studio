"""Add only the separate v0.2 experimental registrations; preserve all v0.1 rows."""
import json
from pathlib import Path
from app.core.config import settings
assert settings.database_url.endswith("/pt_parameter_sandbox")
from app.main import app
from app.db import SessionLocal
from app.models.service import Service
from app.models.operation_contract import OperationContract
from app.schemas.operation_contract import OperationContractWrite

records=json.loads(Path("/review/chain_contracts.json").read_text())
owner=json.loads(Path("/private/credentials.json").read_text())["owner_id"]
with SessionLocal() as db:
    for item in records:
        if db.get(Service,item["service_id"]) or db.get(OperationContract,item["id"]):
            raise ValueError("Versioned registration already exists; do not mutate its definitions")
    for item in records:
        value=OperationContractWrite.model_validate({k:v for k,v in item.items() if k not in {"id","service_id"}})
        method=value.runtime_operation_name
        db.add(Service(id=item["service_id"],name="EXPERIMENTAL Portuguese chained "+method,
            provider="Platform-controlled sandbox; no partner approval",category="experimental-portuguese",
            description="Version 0.2 guarded model handoff, synthetic local verification only.",
            status="approved",lifecycle_status="active",version="0.2.0",operation_name=method,
            container_name="pt-chain-"+method,interface_type="control",orchestration_mode="sidecar",adapter_type="platform-experimental",
            contract_uri=value.operation_identity,internal_host="pt-adapter",internal_port="8080",health_path="/health",
            image="sha256:1305664435c30980c2649defc1a798fc2262e9ca835f8348ecbe2c43ae89034f",
            input_type="authorized dataset reference (dataset_ref)" if method=="TrainModel" else "authorized model reference (model_ref)",
            output_type="authorized model reference (model_ref)" if method=="TrainModel" else "CSV time-series sequences",
            created_by_user_id=owner))
        db.flush();values=value.model_dump();values["definition"]=value.definition.model_dump(mode="json",exclude_none=True)
        values["source_reference"]="https://github.com/AI-EFFECT/ai-effect-wp3/tree/30e1ac403c7434149f3ff3568843f2cc75702413/experimental/portuguese_parameters"
        db.add(OperationContract(id=item["id"],service_id=item["service_id"],status="active",**values))
    db.commit()
print("Added two separate v0.2 experimental registrations; all historical contracts and designs preserved; no execution.")
