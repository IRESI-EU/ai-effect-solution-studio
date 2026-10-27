from typing import Any

import requests
from fastapi import HTTPException

from app.core.config import settings


def _orchestrator_headers() -> dict[str, str]:
    if not settings.orchestrator_api_key:
        return {}

    return {"Authorization": f"Bearer {settings.orchestrator_api_key}"}


def require_parameter_transport(compiled):
    try:
        response = requests.get(f"{settings.orchestrator_base_url}/capabilities", headers=_orchestrator_headers(), timeout=5)
        capability = response.json() if response.status_code == 200 else None
        if (not isinstance(capability, dict) or capability.get("capability_schema_version") != "1.0"
                or not isinstance(capability.get("transports"), list)
                or "http-parameters-v1" not in capability["transports"]
                or capability.get("parameter_validation") != "wrapper-contract-v1"):
            raise ValueError("Runtime cannot verify target-wrapper parameter contracts")
        # This endpoint is read-only: it never initializes tasks or starts a workflow.
        checked = requests.post(f"{settings.orchestrator_base_url}/workflows/check-compatibility",
            json={key: compiled[key] for key in ("blueprint", "dockerinfo", "task_configurations", "services_api_key") if key in compiled},
            headers=_orchestrator_headers(), timeout=20)
        report = checked.json() if checked.status_code == 200 else None
        expected = {node["node_key"]: node for node in compiled["solution_studio_metadata"]["execution_instances"] if node["configuration"]}
        if not isinstance(report, dict) or report.get("status") != "ready" or set(report.get("checks", {})) != set(expected):
            raise ValueError("Target wrapper compatibility is unavailable or rejected")
        for key, node in expected.items():
            check, configuration = report["checks"][key], node["configuration"]
            if any(check.get(field) != configuration[field] for field in ("operation_identity", "contract_version", "schema_version")):
                raise ValueError("Target wrapper operation/contract version differs from the saved instance")
            if check.get("parameter_contract_sha256") != node["parameter_contract_sha256"]:
                raise ValueError("Target wrapper parameter definition differs from the operation registry")
        return report
    except (requests.RequestException, ValueError, TypeError, KeyError, AttributeError):
        raise HTTPException(409, "Parameter compatibility could not be confirmed for this runtime and its target wrappers. Check the declared operation/contract/protocol versions; no workflow was submitted.") from None


def _read_response_detail(response: requests.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text


def _raise_orchestrator_error(
    *,
    response: requests.Response,
    url: str,
    action: str,
) -> None:
    raise HTTPException(
        status_code=response.status_code,
        detail={
            "message": f"WP3 orchestrator rejected the {action}.",
            "orchestrator_url": url,
            "orchestrator_status": response.status_code,
            "orchestrator_detail": _read_response_detail(response),
        },
    )


def _raise_connection_error(
    *,
    exc: requests.RequestException,
    url: str,
    action: str,
) -> None:
    raise HTTPException(
        status_code=502,
        detail={
            "message": f"Could not reach the WP3 orchestrator while trying to {action}.",
            "orchestrator_url": url,
            "error": str(exc),
        },
    ) from exc


def submit_to_orchestrator(payload: dict[str, Any]) -> dict[str, Any]:
    url = f"{settings.orchestrator_base_url}/workflows"

    try:
        response = requests.post(
            url,
            json=payload,
            headers=_orchestrator_headers(),
            timeout=20,
        )
    except requests.RequestException as exc:
        _raise_connection_error(
            exc=exc,
            url=url,
            action="submit workflow",
        )

    if response.status_code >= 400:
        _raise_orchestrator_error(
            response=response,
            url=url,
            action="workflow submission",
        )

    try:
        return response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "WP3 orchestrator returned a non-JSON response for workflow submission.",
                "orchestrator_url": url,
                "response_text": response.text,
            },
        ) from exc


def get_workflow_status(workflow_id: str) -> dict[str, Any]:
    url = f"{settings.orchestrator_base_url}/workflows/{workflow_id}"

    try:
        response = requests.get(
            url,
            headers=_orchestrator_headers(),
            timeout=10,
        )
    except requests.RequestException as exc:
        _raise_connection_error(
            exc=exc,
            url=url,
            action="fetch workflow status",
        )

    if response.status_code >= 400:
        _raise_orchestrator_error(
            response=response,
            url=url,
            action="workflow status request",
        )

    try:
        return response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "WP3 orchestrator returned a non-JSON workflow status response.",
                "orchestrator_url": url,
                "response_text": response.text,
            },
        ) from exc


def get_workflow_tasks(workflow_id: str) -> dict[str, Any]:
    url = f"{settings.orchestrator_base_url}/workflows/{workflow_id}/tasks"

    try:
        response = requests.get(
            url,
            headers=_orchestrator_headers(),
            timeout=10,
        )
    except requests.RequestException as exc:
        _raise_connection_error(
            exc=exc,
            url=url,
            action="fetch workflow tasks",
        )

    if response.status_code >= 400:
        _raise_orchestrator_error(
            response=response,
            url=url,
            action="workflow tasks request",
        )

    try:
        return response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "WP3 orchestrator returned a non-JSON workflow tasks response.",
                "orchestrator_url": url,
                "response_text": response.text,
            },
        ) from exc
