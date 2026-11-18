"""Bounded discovery from provider-supplied JSON Schema/OpenAPI. No network or AI calls.

Suggestions are evidence, not approvals. Unsupported schemas remain visible and
cannot silently lose constraints when converted to the small parameter core.
"""
import hashlib
import json
import re
from typing import Any
from uuid import uuid4

from app.schemas.operation_contract import ParameterDefinition


MAX_DOCUMENT_BYTES = 256_000
NAME = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
SECRET = re.compile(r"password|passwd|secret|token|credential|api[_-]?key|authorization|private[_-]?key", re.I)
OPERATOR = re.compile(r"(^|_)(host|port|path|dir|directory|mount|image|endpoint|url|uri)($|_)", re.I)
DATA = re.compile(r"(^|_)(data|dataset|file|csv|model_ref|input_ref)($|_)", re.I)
SUPPORTED_KEYS = {"type", "title", "description", "default", "minimum", "maximum", "enum", "x-unit", "x-ai-effect-kind"}
ANNOTATIONS = {"$schema", "$id", "$comment", "examples", "example", "deprecated"}


def reviewed_contract_digest(contract) -> str:
    return hashlib.sha256(json.dumps({"definition": contract.definition, "operation_identity": contract.operation_identity,
                                     "runtime_operation_name": contract.runtime_operation_name, "contract_version": contract.contract_version},
                                    sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def reviewed_service_digest(service) -> str:
    fields = ("version", "operation_name", "interface_type", "orchestration_mode", "adapter_type", "image", "container_name",
              "internal_host", "internal_port", "repository_url", "repository_branch", "manifest_path", "proto_uri",
              "contract_uri", "input_type", "output_type")
    return hashlib.sha256(json.dumps({key: getattr(service, key, None) for key in fields}, sort_keys=True,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _pointer(text: str) -> str:
    return text.replace("~", "~0").replace("/", "~1")


def _resolve(document: dict, value: Any, pointer: str) -> tuple[dict, str]:
    """Resolve only local references, with a depth bound and no external I/O."""
    seen = set()
    for _ in range(12):
        if not isinstance(value, dict):
            raise ValueError("Expected a schema object")
        ref = value.get("$ref")
        if not ref:
            return value, pointer
        if len(value) != 1 or not isinstance(ref, str) or not ref.startswith("#/") or ref in seen:
            raise ValueError("Only acyclic local references without sibling constraints are supported")
        seen.add(ref)
        pointer = ref
        value = document
        for part in ref[2:].split("/"):
            if not isinstance(value, dict) or part.replace("~1", "/").replace("~0", "~") not in value:
                raise ValueError("Unresolved local schema reference")
            value = value[part.replace("~1", "/").replace("~0", "~")]
    raise ValueError("Schema reference depth exceeded")


def classify(name: str, schema: dict) -> str:
    name = re.sub(r"([a-z])([A-Z])", r"\1_\2", name)
    kind = schema.get("x-ai-effect-kind")
    if SECRET.search(name) or schema.get("writeOnly") or schema.get("format") == "password" or kind == "secret":
        return "secret"
    if OPERATOR.search(name) or kind == "operator":
        return "operator"
    if DATA.search(name) or kind == "data_input" or schema.get("format") in {"binary", "byte", "uri"}:
        return "data_input"
    return "setting"


def discover(document: dict, source_reference: str, operation_name: str, operation_id: str | None = None) -> dict:
    encoded = json.dumps(document, sort_keys=True, allow_nan=False).encode()
    if len(encoded) > MAX_DOCUMENT_BYTES:
        raise ValueError("Interface description exceeds the 256 KB discovery limit")
    source_reference = source_reference.strip()
    if not source_reference:
        raise ValueError("Supply a source reference")
    pointer = "#"
    if "openapi" in document:
        selected = []
        paths = document.get("paths", {})
        if not isinstance(paths, dict):
            raise ValueError("OpenAPI paths must be an object")
        for path, methods in paths.items():
            if not isinstance(methods, dict):
                continue
            for method, operation in methods.items():
                if method.lower() not in {"post", "put", "patch", "get", "delete"} or not isinstance(operation, dict):
                    continue
                if operation.get("operationId") == (operation_id or operation_name):
                    selected.append((path, method, operation))
        if len(selected) != 1:
            raise ValueError("Select one unique OpenAPI operationId for this service")
        path, method, operation = selected[0]
        pointer = f"#/paths/{_pointer(path)}/{method}/requestBody"
        body, pointer = _resolve(document, operation.get("requestBody", {}), pointer)
        contents = body.get("content", {})
        if not isinstance(contents, dict) or not isinstance(contents.get("application/json", {}), dict):
            raise ValueError("OpenAPI request content must be an object")
        content = contents.get("application/json", {})
        root, pointer = _resolve(document, content.get("schema", {}), pointer + "/content/application~1json/schema")
    else:
        root, pointer = _resolve(document, document, pointer)
    if root.get("type") != "object" or not isinstance(root.get("properties"), dict):
        raise ValueError("Supply an object JSON Schema or a selected OpenAPI JSON request body")
    # A control envelope has one documented parameters object. Inputs and operator
    # fields outside it are not guessed to be algorithm settings.
    if "configuration" in root["properties"]:
        configuration, configuration_pointer = _resolve(document, root["properties"]["configuration"], pointer + "/properties/configuration")
        if isinstance(configuration.get("properties"), dict) and "parameters" in configuration["properties"]:
            root, pointer = configuration, configuration_pointer
    if "parameters" in root["properties"]:
        root, pointer = _resolve(document, root["properties"]["parameters"], pointer + "/properties/parameters")
    if root.get("type") != "object" or not isinstance(root.get("properties"), dict):
        raise ValueError("The parameters schema must describe an object")
    if len(root["properties"]) > 100:
        raise ValueError("At most 100 fields can be reviewed in one operation")
    root_constraints = set(root) - {"type", "properties", "required", "additionalProperties", "title", "description"} - ANNOTATIONS
    required = root.get("required", [])
    if not isinstance(required, list) or any(not isinstance(name, str) for name in required):
        raise ValueError("Schema required must be an array of field names")
    candidates = []
    for name, raw in root["properties"].items():
        source_pointer = f"{pointer}/properties/{_pointer(name)}"
        reason = None
        try:
            schema, source_pointer = _resolve(document, raw, source_pointer)
        except ValueError as exc:
            schema, reason = {}, str(exc)
        kind = classify(name, schema)
        if kind != "setting":
            # Never retain secret/default values or docs for excluded fields.
            candidates.append({"name": name, "source_pointer": source_pointer, "classification": kind,
                               "supported": False, "reason": f"Keep {kind.replace('_', ' ')} outside algorithm settings"})
            continue
        if not NAME.fullmatch(name):
            reason = "The parameter core requires a lowercase identifier"
        unsupported = set(schema) - SUPPORTED_KEYS - ANNOTATIONS
        if unsupported or root_constraints:
            reason = "Unsupported constraints need an explicit interface update: " + ", ".join(sorted(unsupported | root_constraints))
        if root.get("additionalProperties") not in (None, False, True):
            reason = "Typed additional properties require connector support"
        spec = {key: value for key, value in schema.items() if key in {"type", "title", "description", "default", "minimum", "maximum", "enum"}}
        spec["required"] = name in required
        # Missing descriptions stay blank: the provider supplies the meaning.
        spec.setdefault("title", name)
        spec.setdefault("description", "")
        if isinstance(schema.get("x-unit"), str):
            spec["unit"] = schema["x-unit"]
        supported = not reason and isinstance(schema.get("type"), str) and schema["type"] in {"integer", "number", "boolean", "string"}
        if schema.get("type") == "string" and not schema.get("enum"):
            supported, reason = False, "Free text is not supported by the parameter core; use a confirmed enumeration"
        if not supported and not reason:
            reason = "Complex values need connector support; separate data inputs from settings"
        if supported:
            try:
                trial = ParameterDefinition.model_validate({**spec, "description": spec["description"] or "Meaning requires provider review"})
                validate_reviewed_definition(name, trial)
                from app.services.parameter_values import parameter_contract_digest
                parameter_contract_digest({"schema_version": "1.0", "transport": "http-parameters-v1", "properties": {name: trial.model_dump(exclude_none=True)}})
            except ValueError:
                supported, reason = False, "This declaration has an invalid type, default, choice or bound; supply a corrected interface description"
        if not supported:
            spec.pop("default", None)
            spec.pop("enum", None)
        candidates.append({"name": name, "source_pointer": source_pointer, "classification": "setting",
                           "supported": bool(supported), "reason": reason, "definition": spec,
                           "unit": schema.get("x-unit")})
    return {"revision": uuid4().hex, "operation_name": operation_name, "source_reference": source_reference,
            "source_sha256": hashlib.sha256(encoded).hexdigest(), "candidates": candidates,
            "status": "awaiting_provider_review"}


def validate_reviewed_definition(name: str, spec: ParameterDefinition) -> None:
    # The same exclusion policy applies to hand-edited requests.
    if classify(name, {}) != "setting":
        raise ValueError("Data inputs, secrets and operator fields cannot be exposed as settings")
    if not spec.title.strip() or not spec.description.strip():
        raise ValueError("Each selected parameter needs a clear label and meaning")
    if spec.type not in {"integer", "number"} and (spec.minimum is not None or spec.maximum is not None):
        raise ValueError("Numeric limits apply only to integer and number settings")
