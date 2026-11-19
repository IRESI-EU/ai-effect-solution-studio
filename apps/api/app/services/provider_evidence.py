"""Opt-in private evidence, using the existing provider audit logger.

Diagnostic data only: never a source of settings, authority or accounting state.
No prompts, headers, raw wire payloads or hidden reasoning are retained.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import json
import logging
import re

from app.services.shared_allowance import safe_usage

_correlation = ContextVar("provider_evidence_correlation", default=None)
_private_key = re.compile(r"secret|password|token|authorization|api.?key|path|uploaded_file|dataset_bytes|csv_bytes|raw_data", re.I)


@contextmanager
def correlation(*, conversation_id, draft_id, revision):
    # Browser conversation IDs are correlation only, never ownership/authority.
    token = _correlation.set(dict(conversation_id=conversation_id, draft_id=draft_id, revision=revision))
    try:
        yield
    finally:
        _correlation.reset(token)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        allow_nan=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def sanitize(value):
    """Evidence-only redaction; does not change model input or validated output."""
    if isinstance(value, dict):
        return {key: sanitize(item) for key, item in value.items() if not _private_key.search(key)}
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, str):
        # Edit values may themselves be serialized objects. Treat them as data.
        if value.lstrip().startswith(("{", "[")):
            try:
                return json.dumps(sanitize(json.loads(value)), ensure_ascii=False)
            except (ValueError, TypeError):
                pass
        # Multi-row CSV content has no place in a text-only audit record.
        lines = value.strip().splitlines()
        if any("," in left and "," in right for left, right in zip(lines, lines[1:])):
            return "[dataset content omitted]"
        value = re.sub(r"(?:https?://|file://|data:)\S+", "[reference omitted]", value, flags=re.I)
        if re.search(r"[A-Za-z]:[\\/]|\\\\|(?<![\w:])/[^\s]+", value):
            # Omit the entire field, including paths containing spaces.
            return "[private path omitted]"
        value = re.sub(r"\b(?:sk-[A-Za-z0-9_-]+|Bearer\s+\S+)", "[redacted]", value, flags=re.I)
        value = re.sub(r"(?i)(password|secret|api[_ -]?key|token|authorization)\s*[:=]\s*\S+", r"\1=[redacted]", value)
    return value


def identifier(value):
    return value if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.:-]{1,200}", value) else None


def request_identifier(raw):
    try:
        return identifier(getattr(raw.http_response, "headers", {}).get("x-request-id"))
    except Exception:
        return None


def begin(kwargs, reservation, remote, timeout):
    if not logging.getLogger("design_ai.provider.audit").isEnabledFor(logging.DEBUG):
        return None
    try:
        config = {key: kwargs[key] for key in ("model", "store", "service_tier", "max_output_tokens", "reasoning", "prompt_cache_options") if key in kwargs}
        config["transport"] = {"endpoint": "responses", "max_retries": 0, "timeout_seconds": timeout}
        schema = kwargs["text_format"].model_json_schema()
        return dict(audit_format_version=3,
            requested_model=identifier(kwargs.get("model")),
            requested_service_tier=identifier(kwargs.get("service_tier")),
            requested_configuration=config,
            request_sha256=digest({"configuration": config, "input": kwargs["input"], "schema": schema}),
            configuration_sha256=digest({"configuration": config, "schema": schema}),
            correlation={key: (value if key == "revision" and type(value) is int else identifier(value))
                for key, value in {"conversation_id": None, "draft_id": None, "revision": None, **(_correlation.get() or {}),
                "accounting_permit": str(reservation) if reservation is not None else None,
                **({key: remote.claims.get(key) for key in ("scope", "consumer_id", "environment")} if remote else {})}.items()})
    except Exception:
        # Optional diagnostics must never change dispatch or settlement semantics.
        return None


def finish(record, *, payload, response, request_id, validated, stage=None):
    if record is None:
        return
    try:
        def field(key):
            return payload.get(key) if isinstance(payload, dict) else getattr(response, key, None)
        usage = field("usage")
        if hasattr(usage, "model_dump"):
            usage = usage.model_dump(mode="json")
        output = field("output") or []
        texts = [content.get("text", content.get("refusal", ""))
            for item in output if isinstance(item, dict) and item.get("type") == "message"
            for content in (item.get("content") or []) if isinstance(content, dict) and content.get("type") in {"output_text", "refusal"}]
        turn = validated.model_dump(mode="json") if validated is not None else None
        record.update(returned_model=identifier(field("model")), returned_service_tier=identifier(field("service_tier")),
            provider_stage=identifier(stage),
            response_id=identifier(field("id")), request_id=identifier(request_id or getattr(response, "_request_id", None)),
            status=identifier(field("status")), usage=safe_usage(usage),
            validated_response=sanitize(turn), validated_response_sha256=digest(turn) if turn is not None else None,
            validation="sdk_schema_validated; canonical application validation remains separate" if turn is not None else "unavailable: no validated structured response",
            visible_output=sanitize(texts))
        record["unavailable_fields"] = [key for key in ("returned_model", "returned_service_tier", "response_id", "request_id", "status", "usage", "validated_response") if record[key] is None]
        logging.getLogger("design_ai.provider.audit").debug(json.dumps(record, ensure_ascii=False, allow_nan=False))
    except Exception:
        # Includes file/serialization errors. Never retry a model/accounting call.
        pass
