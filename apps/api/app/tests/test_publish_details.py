"""Publishing: plain-language description, adjustable settings and the connection test."""

from app.schemas.service_import import ValidationMessage
from app.services.runtime_preflight import check_declared_runtime
from app.services.service_manifest_importer import normalize_manifest


def manifest(**extra):
    base = {
        "schema_version": "1.0",
        "service": {"id": "test-forecaster", "name": "Forecaster", "provider": "Node", "category": "Forecasting",
                    "version": "1.0.0", "description": "Forecasts load."},
        "runtime": {"type": "docker", "container_name": "forecaster", "image": "node/forecaster:1.0.0",
                    "internal_port": "8080", "health_path": "/health"},
        "interface": {"type": "control", "operation_name": "Forecast", "input_type": "Workflow Start",
                      "output_type": "Workflow Output"},
    }
    base.update(extra)
    return base


def normalise(data):
    validation: list[ValidationMessage] = []
    service = normalize_manifest(data, "provider-supplied", "unversioned", "guided.json", validation)
    return service, validation


def test_design_text_is_kept_and_trimmed():
    service, _ = normalise(manifest(design={
        "purpose": "  Forecasts household load.  ", "use_when": "Before planning flexibility.",
        "keywords": ["load", "forecast", 3, ""], "unknown": "dropped",
    }))
    assert service.interface_contract["design"] == {
        "purpose": "Forecasts household load.",
        "use_when": "Before planning flexibility.",
        "keywords": ["load", "forecast", "3"],
    }


def test_valid_settings_are_stored_like_the_settings_endpoint():
    settings = {"channel": "parameters", "schema": {"type": "object", "properties": {
        "horizon": {"type": "integer", "title": "Horizon", "default": 24, "minimum": 1, "maximum": 168},
    }}}
    service, validation = normalise(manifest(settings=settings))
    assert service.interface_contract["settings"]["schema"]["properties"]["horizon"]["default"] == 24
    assert any(item.level == "success" and "1 adjustable setting declared" in item.message for item in validation)


def test_invalid_settings_are_reported_not_stored():
    bad = {"channel": "somewhere", "schema": {"type": "object", "properties": {}}}
    service, validation = normalise(manifest(settings=bad))
    assert "settings" not in service.interface_contract
    assert any(item.level == "error" and item.message.startswith("settings:") for item in validation)


def test_manifest_without_extras_is_unchanged():
    service, _ = normalise(manifest())
    assert "design" not in service.interface_contract and "settings" not in service.interface_contract


def test_connection_test_refuses_the_platform_itself():
    for host in ("localhost", "127.0.0.1", "postgres", "169.254.169.254", "[::1]"):
        result = check_declared_runtime(host, "8080", "/health")
        assert result["status"] == "misconfigured", host
        assert "platform itself" in result["message"]


def test_connection_test_reports_bad_addresses_and_unknown_hosts():
    assert check_declared_runtime("forecaster", "not-a-port", "/health")["status"] == "misconfigured"
    unknown = check_declared_runtime("no-such-service.invalid", "8080", "/health")
    assert unknown["status"] == "unavailable"
    assert set(unknown) == {"status", "message", "recommended_action", "http_status", "runtime_url", "failure_reason"}
