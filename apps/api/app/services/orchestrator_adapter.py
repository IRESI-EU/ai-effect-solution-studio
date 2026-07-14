from typing import Any

import requests
from fastapi import HTTPException

from app.core.config import settings


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
        response = requests.post(url, json=payload, timeout=20)
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
        response = requests.get(url, timeout=10)
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
        response = requests.get(url, timeout=10)
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