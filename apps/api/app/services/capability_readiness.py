"""Read-only checks from the API's actual runtime network."""
import requests
from fastapi import HTTPException


def require_binding_transport(compiled):
    report = compiled["solution_studio_metadata"]["capability_bindings"]
    if report["status"] != "verified":
        return {"status": "unqualified"}
    instances = {n["instance_id"]: n for n in compiled["solution_studio_metadata"]["execution_instances"]}
    endpoints = {n["container_name"]: n for n in compiled["dockerinfo"]["docker_info_list"]}
    checks = {}
    try:
        for key, contract in report["contracts"].items():
            endpoint = endpoints[instances[key]["node_key"].split(":")[0]]
            token = compiled.get("services_api_key")
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            response = requests.get(f"http://{endpoint['ip_address']}:{endpoint['port']}/control/capabilities",
                                    headers=headers, timeout=5, allow_redirects=False)
            if response.status_code != 200:
                raise ValueError()
            response.raise_for_status()
            value = response.json()
            if not isinstance(value, dict) or not isinstance(value.get("operations"), list):
                raise ValueError()
            matches = [o for o in value["operations"] if isinstance(o, dict) and o.get("operation_name") == contract["runtime_operation_name"]]
            if value.get("capability_schema_version") != "1.0" or len(matches) != 1:
                raise ValueError()
            operation = matches[0]
            if any(operation.get(k) != contract[k] for k in ("operation_identity", "contract_version")):
                raise ValueError()
            if (operation.get("binding_transport") != "whole-output-v1"
                    or operation.get("io_contract_sha256") != contract["definition_sha256"]):
                raise ValueError()
            checks[key] = {"status": "ready", "contract_version": contract["contract_version"],
                           "definition_sha256": contract["definition_sha256"]}
    except (requests.RequestException, ValueError, KeyError, TypeError):
        raise HTTPException(409, "Connection readiness could not be verified. The service is unavailable or its runtime contract differs from the saved design. No workflow was submitted.") from None
    return {"status": "ready", "checks": checks}
