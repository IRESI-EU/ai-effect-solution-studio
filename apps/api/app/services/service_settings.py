"""Adjustable service settings.

A service may declare settings that it already reads at run time. The
declaration is stored in ``service.interface_contract["settings"]``:

    {
      "channel": "parameters" | "run_input",
      "schema": {
        "type": "object",
        "properties": {
          "epochs": {"type": "integer", "title": "Epochs", "default": 5, "minimum": 1}
        },
        "required": []
      }
    }

``parameters`` settings are sent in the ``parameters`` field of the service's
``/control/execute`` call. ``run_input`` settings are sent as the service's
inline JSON input, which only start nodes receive. ``schema`` is a small,
validated subset of JSON Schema (flat object of scalar, array or object
properties) so it can drive a form, be checked here and be read by Design with
AI. A service without a declaration has fixed settings.
"""

from __future__ import annotations

import math
from typing import Any

SETTINGS_KEY = "settings"
CHANNELS = ("parameters", "run_input")
PROPERTY_TYPES = ("string", "integer", "number", "boolean", "array", "object")
PROPERTY_KEYS = {
    "type", "title", "description", "default", "minimum", "maximum",
    "enum", "minLength", "maxLength", "unit",
}
MAX_PROPERTIES = 50


class SettingsDefinitionError(ValueError):
    """Raised when a settings declaration is malformed."""


def _type_matches(value: Any, expected: str) -> bool:
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
        )
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    return False


def _check_value(name: str, value: Any, prop: dict[str, Any]) -> str | None:
    """Return an error message for a value, or None when it is valid."""
    expected = prop["type"]
    if not _type_matches(value, expected):
        return f"'{name}' must be of type {expected}"
    if "enum" in prop and value not in prop["enum"]:
        allowed = ", ".join(repr(v) for v in prop["enum"])
        return f"'{name}' must be one of: {allowed}"
    if expected in ("integer", "number"):
        if "minimum" in prop and value < prop["minimum"]:
            return f"'{name}' must be at least {prop['minimum']}"
        if "maximum" in prop and value > prop["maximum"]:
            return f"'{name}' must be at most {prop['maximum']}"
    if expected == "string":
        if "minLength" in prop and len(value) < prop["minLength"]:
            return f"'{name}' must have at least {prop['minLength']} characters"
        if "maxLength" in prop and len(value) > prop["maxLength"]:
            return f"'{name}' must have at most {prop['maxLength']} characters"
    return None


def normalize_definition(raw: Any) -> dict[str, Any]:
    """Validate a settings declaration and return a normalised copy."""
    if not isinstance(raw, dict):
        raise SettingsDefinitionError("settings must be an object")
    unknown_top = set(raw) - {"channel", "schema"}
    if unknown_top:
        raise SettingsDefinitionError(f"unknown settings fields: {', '.join(sorted(unknown_top))}")

    channel = raw.get("channel", "parameters")
    if channel not in CHANNELS:
        raise SettingsDefinitionError(f"channel must be one of: {', '.join(CHANNELS)}")

    schema = raw.get("schema")
    if not isinstance(schema, dict) or schema.get("type", "object") != "object":
        raise SettingsDefinitionError("schema must be a JSON Schema object with type 'object'")
    properties = schema.get("properties")
    if not isinstance(properties, dict) or not properties:
        raise SettingsDefinitionError("schema.properties must declare at least one setting")
    if len(properties) > MAX_PROPERTIES:
        raise SettingsDefinitionError(f"at most {MAX_PROPERTIES} settings can be declared")

    normalized_props: dict[str, dict[str, Any]] = {}
    for name, prop in properties.items():
        if not isinstance(name, str) or not name.strip():
            raise SettingsDefinitionError("setting names must be non-empty strings")
        if not isinstance(prop, dict):
            raise SettingsDefinitionError(f"setting '{name}' must be an object")
        unknown = set(prop) - PROPERTY_KEYS
        if unknown:
            raise SettingsDefinitionError(
                f"setting '{name}' has unsupported fields: {', '.join(sorted(unknown))}"
            )
        if prop.get("type") not in PROPERTY_TYPES:
            raise SettingsDefinitionError(
                f"setting '{name}' must have type one of: {', '.join(PROPERTY_TYPES)}"
            )
        if "enum" in prop and (not isinstance(prop["enum"], list) or not prop["enum"]):
            raise SettingsDefinitionError(f"setting '{name}' enum must be a non-empty list")
        for bound in ("minimum", "maximum"):
            if bound in prop and not _type_matches(prop[bound], "number"):
                raise SettingsDefinitionError(f"setting '{name}' {bound} must be a number")
        if "minimum" in prop and "maximum" in prop and prop["minimum"] > prop["maximum"]:
            raise SettingsDefinitionError(f"setting '{name}' minimum is greater than maximum")
        clean = dict(prop)
        if "default" in clean:
            error = _check_value(name, clean["default"], clean)
            if error:
                raise SettingsDefinitionError(f"default for {error}")
        normalized_props[name] = clean

    required = schema.get("required", [])
    if not isinstance(required, list) or any(r not in normalized_props for r in required):
        raise SettingsDefinitionError("schema.required must list declared settings only")

    return {
        "channel": channel,
        "schema": {
            "type": "object",
            "properties": normalized_props,
            "required": list(required),
            "additionalProperties": False,
        },
    }


def get_definition(service: Any) -> dict[str, Any] | None:
    """Return the service's settings declaration, or None for fixed settings."""
    contract = getattr(service, "interface_contract", None) or {}
    definition = contract.get(SETTINGS_KEY) if isinstance(contract, dict) else None
    return definition or None


def resolve_values(
    definition: dict[str, Any],
    values: dict[str, Any] | None,
) -> tuple[dict[str, Any], list[str]]:
    """Merge saved values over defaults and validate them.

    Returns the effective values and a list of error messages. Values for
    settings that are not declared are reported, never silently sent.
    """
    values = values or {}
    if not isinstance(values, dict):
        return {}, ["settings values must be an object"]
    properties = definition["schema"]["properties"]
    errors: list[str] = []

    for name in values:
        if name not in properties:
            errors.append(f"'{name}' is not a setting of this service")

    effective: dict[str, Any] = {}
    for name, prop in properties.items():
        if name in values and values[name] is not None:
            value = values[name]
        elif "default" in prop:
            value = prop["default"]
        else:
            if name in definition["schema"].get("required", []):
                errors.append(f"'{name}' is required")
            continue
        error = _check_value(name, value, prop)
        if error:
            errors.append(error)
        else:
            effective[name] = value

    return effective, errors
