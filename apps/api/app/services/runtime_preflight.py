from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit

import requests
from sqlalchemy.orm import Session

from app.models.service import Service


RUNTIME_HEALTH_TIMEOUT_SECONDS = 2
LEGACY_RUNTIME_MANAGEMENT_MODE = "provider_managed"
DEPLOYMENT_ELIGIBLE_STATUSES = {"approved", "validated"}


def run_runtime_preflight(workflow_nodes, db: Session):
    """Check governance eligibility and runtime health for every workflow service."""
    checks = []

    for node in workflow_nodes:
        node_id = getattr(node, "node_id", "")
        service_id = getattr(node, "service_id", None)

        if not service_id:
            checks.append(
                _result_check(
                    node_id=node_id,
                    service_id="",
                    service_name="Unconfigured service",
                    responsible_party="Solution designer",
                    status="misconfigured",
                    message="This workflow item does not identify a catalogue service.",
                    recommended_action="Remove this item or select a catalogue service, then validate the design again.",
                )
            )
            continue

        service = db.query(Service).filter(Service.id == service_id).first()

        if not service:
            checks.append(
                _result_check(
                    node_id=node_id,
                    service_id=service_id,
                    service_name=service_id,
                    responsible_party="Service publisher",
                    status="unknown",
                    message="The referenced service does not exist in the catalogue.",
                    recommended_action="Replace this service selection with an available catalogue service.",
                )
            )
            continue

        governance_message = _governance_blocker(service)
        if governance_message:
            checks.append(
                _result_check(
                    node_id=node_id,
                    service_id=service.id,
                    service_name=service.name,
                    responsible_party=service.provider or "Service provider",
                    status="ineligible",
                    message=governance_message,
                    recommended_action="Ask the service provider or platform operator to approve and activate the service, or choose another eligible service.",
                )
            )
            continue

        runtime_url, url_error = build_runtime_health_url(service)
        if url_error:
            checks.append(
                _result_check(
                    node_id=node_id,
                    service_id=service.id,
                    service_name=service.name,
                    responsible_party=service.provider or "Service provider",
                    status="misconfigured",
                    message=url_error,
                    recommended_action="Ask the service provider to correct the runtime host, port, and health path metadata.",
                )
            )
            continue

        checks.append(_check_runtime(node, service, runtime_url))

    counts = {
        status: sum(1 for check in checks if check["status"] == status)
        for status in ("ready", "unavailable", "misconfigured", "ineligible", "unknown")
    }
    blocking_count = sum(1 for check in checks if check["blocking"])
    total_services = len(checks)
    blocking_service_label = "service" if blocking_count == 1 else "services"
    blocking_verb = "requires" if blocking_count == 1 else "require"

    return {
        "status": "blocked" if total_services == 0 or blocking_count else "ready",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_services": total_services,
            "ready": counts["ready"],
            "blocked": blocking_count if total_services else 1,
            "unavailable": counts["unavailable"],
            "misconfigured": counts["misconfigured"],
            "ineligible": counts["ineligible"],
            "unknown": counts["unknown"],
            "message": (
                "No services were provided."
                if total_services == 0
                else (
                    "All services are eligible and their runtimes are ready."
                    if blocking_count == 0
                    else f"{blocking_count} {blocking_service_label} {blocking_verb} action before deployment."
                )
            ),
        },
        "checks": checks,
    }


def build_runtime_health_url(service: Service):
    host = (service.internal_host or "").strip()
    port = (service.internal_port or "").strip()
    health_path = (service.health_path or "/health").strip() or "/health"

    if not host:
        return None, "Runtime metadata is missing the internal host."

    if not port:
        return None, "Runtime metadata is missing the internal port."

    try:
        port_number = int(port)
    except (TypeError, ValueError):
        return None, "Runtime metadata contains an invalid internal port."

    if not 1 <= port_number <= 65535:
        return None, "Runtime metadata contains an invalid internal port."

    host_with_scheme = host if "://" in host else f"http://{host}"

    try:
        parsed_host = urlsplit(host_with_scheme)
        if parsed_host.scheme not in {"http", "https"} or not parsed_host.hostname:
            return None, "Runtime metadata contains a malformed internal host."
        if parsed_host.username or parsed_host.password:
            return None, "Runtime metadata contains a malformed internal host."
        if parsed_host.path not in {"", "/"} or parsed_host.query or parsed_host.fragment:
            return None, "Runtime metadata contains a malformed internal host."
        parsed_host.port
    except ValueError:
        return None, "Runtime metadata contains a malformed internal host."

    hostname = parsed_host.hostname
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"

    if not health_path.startswith("/"):
        health_path = f"/{health_path}"

    parsed_health_path = urlsplit(health_path)
    if (
        health_path.startswith("//")
        or parsed_health_path.scheme
        or parsed_health_path.netloc
        or parsed_health_path.query
        or parsed_health_path.fragment
        or any(character.isspace() for character in health_path)
    ):
        return None, "Runtime metadata contains a malformed health path."

    runtime_url = urlunsplit(
        (parsed_host.scheme, f"{hostname}:{port_number}", health_path, "", "")
    )
    return runtime_url, None


def _governance_blocker(service: Service):
    lifecycle_status = (getattr(service, "lifecycle_status", "") or "active").lower()
    service_status = (getattr(service, "status", "") or "").lower()
    trust_badge = (getattr(service, "trust_badge", "") or "").lower()

    if lifecycle_status == "archived":
        return "The service is archived and cannot be used for a new deployment."

    if service_status == "rejected" or trust_badge == "rejected":
        return "The service has been rejected by governance."

    if service_status not in DEPLOYMENT_ELIGIBLE_STATUSES:
        return "The service has not completed governance approval."

    return None


def _check_runtime(node, service: Service, runtime_url: str):
    base_check = {
        "node_id": getattr(node, "node_id", ""),
        "service_id": service.id,
        "service_name": service.name,
        "runtime_url": runtime_url,
        "runtime_management_mode": LEGACY_RUNTIME_MANAGEMENT_MODE,
        "responsible_party": service.provider or "Service provider",
        "http_status": None,
    }

    try:
        response = requests.get(
            runtime_url,
            timeout=RUNTIME_HEALTH_TIMEOUT_SECONDS,
            allow_redirects=False,
        )
    except requests.Timeout:
        return {
            **base_check,
            "status": "unavailable",
            "blocking": True,
            "message": f"The runtime health check did not respond within {RUNTIME_HEALTH_TIMEOUT_SECONDS} seconds.",
            "recommended_action": "Ask the service provider to start or restore the runtime, then prepare the deployment again.",
        }
    except requests.RequestException:
        return {
            **base_check,
            "status": "unavailable",
            "blocking": True,
            "message": "The runtime health endpoint could not be reached.",
            "recommended_action": "Ask the service provider to start or restore the runtime, then prepare the deployment again.",
        }

    is_ready = 200 <= response.status_code < 300
    return {
        **base_check,
        "status": "ready" if is_ready else "unavailable",
        "blocking": not is_ready,
        "message": (
            "The runtime health endpoint is ready."
            if is_ready
            else f"The runtime health endpoint returned HTTP {response.status_code}; a 2xx response is required."
        ),
        "recommended_action": (
            "No action is required."
            if is_ready
            else "Ask the service provider to restore a healthy 2xx response, then prepare the deployment again."
        ),
        "http_status": response.status_code,
    }


def _result_check(
    *,
    node_id,
    service_id,
    service_name,
    responsible_party,
    status,
    message,
    recommended_action,
):
    return {
        "node_id": node_id,
        "service_id": service_id,
        "service_name": service_name,
        "runtime_url": None,
        "runtime_management_mode": LEGACY_RUNTIME_MANAGEMENT_MODE,
        "responsible_party": responsible_party,
        "status": status,
        "blocking": status != "ready",
        "message": message,
        "recommended_action": recommended_action,
        "http_status": None,
    }
