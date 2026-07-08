import base64
import csv
import json
from pathlib import Path
from urllib.parse import urlparse

import requests


MAX_TEXT_PREVIEW_CHARS = 5000
MAX_CSV_ROWS = 20
HTTP_TIMEOUT_SECONDS = 10


def decode_inline_reference(uri: str):
    try:
        decoded = base64.b64decode(uri).decode("utf-8")
    except Exception as exc:
        return {
            "kind": "inline",
            "available": False,
            "message": f"Could not decode inline DataReference: {exc}",
            "uri": uri,
        }

    return parse_content_preview(
        content=decoded,
        format_hint=None,
        source_uri="inline",
        kind="inline",
    )


def preview_file_reference(uri: str):
    path = Path(uri)

    if not path.exists():
        return {
            "kind": "file",
            "available": False,
            "uri": uri,
            "message": (
                "This file reference was produced by a node service, but the file "
                "is not directly available inside the portal API runtime. "
                "For portable artifact preview, node services should expose outputs "
                "using an HTTP, S3, inline, or orchestrator-managed artifact reference."
            ),
            "recommendation": {
                "local_demo": "Mount a shared artifact volume if local file preview is required.",
                "platform_ready": "Prefer http, https, s3, or artifact protocol for future node submissions.",
            },
        }

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return {
            "kind": "file",
            "available": False,
            "uri": uri,
            "message": f"File exists but could not be read by the portal API: {exc}",
        }

    return parse_content_preview(
        content=content,
        format_hint=path.suffix.lower().replace(".", ""),
        source_uri=uri,
        kind="file",
    )


def preview_http_reference(uri: str):
    parsed = urlparse(uri)

    if parsed.scheme not in {"http", "https"}:
        return {
            "kind": "http",
            "available": False,
            "uri": uri,
            "message": "Invalid HTTP DataReference URI.",
        }

    try:
        response = requests.get(uri, timeout=HTTP_TIMEOUT_SECONDS)
        response.raise_for_status()
    except Exception as exc:
        return {
            "kind": "http",
            "available": False,
            "uri": uri,
            "message": f"Could not fetch HTTP DataReference: {exc}",
        }

    content_type = response.headers.get("content-type", "")
    text = response.text

    format_hint = infer_format_from_uri_or_content_type(uri, content_type)

    return parse_content_preview(
        content=text,
        format_hint=format_hint,
        source_uri=uri,
        kind="http",
        content_type=content_type,
    )


def parse_content_preview(
    content: str,
    format_hint: str | None,
    source_uri: str,
    kind: str,
    content_type: str | None = None,
):
    normalized_format = (format_hint or "").lower()

    if normalized_format == "csv" or looks_like_csv(content):
        return preview_csv_content(content, source_uri, kind, content_type)

    if normalized_format == "json" or looks_like_json(content):
        return preview_json_content(content, source_uri, kind, content_type)

    return {
        "kind": kind,
        "available": True,
        "format": normalized_format or "text",
        "uri": source_uri,
        "content_type": content_type,
        "content": content[:MAX_TEXT_PREVIEW_CHARS],
        "truncated": len(content) > MAX_TEXT_PREVIEW_CHARS,
    }


def preview_csv_content(
    content: str,
    source_uri: str,
    kind: str,
    content_type: str | None = None,
):
    try:
        lines = content.splitlines()
        reader = csv.DictReader(lines)

        rows = []
        for index, row in enumerate(reader):
            if index >= MAX_CSV_ROWS:
                break
            rows.append(row)

        return {
            "kind": "csv",
            "available": True,
            "format": "csv",
            "uri": source_uri,
            "content_type": content_type,
            "columns": reader.fieldnames or [],
            "rows": rows,
            "row_preview_limit": MAX_CSV_ROWS,
        }
    except Exception as exc:
        return {
            "kind": kind,
            "available": False,
            "format": "csv",
            "uri": source_uri,
            "content_type": content_type,
            "message": f"Could not parse CSV DataReference: {exc}",
            "content": content[:MAX_TEXT_PREVIEW_CHARS],
        }


def preview_json_content(
    content: str,
    source_uri: str,
    kind: str,
    content_type: str | None = None,
):
    try:
        parsed = json.loads(content)

        return {
            "kind": "json",
            "available": True,
            "format": "json",
            "uri": source_uri,
            "content_type": content_type,
            "content": parsed,
        }
    except Exception as exc:
        return {
            "kind": kind,
            "available": False,
            "format": "json",
            "uri": source_uri,
            "content_type": content_type,
            "message": f"Could not parse JSON DataReference: {exc}",
            "content": content[:MAX_TEXT_PREVIEW_CHARS],
        }


def infer_format_from_uri_or_content_type(uri: str, content_type: str):
    suffix = Path(urlparse(uri).path).suffix.lower().replace(".", "")

    if suffix:
        return suffix

    content_type = content_type.lower()

    if "json" in content_type:
        return "json"

    if "csv" in content_type:
        return "csv"

    if "text" in content_type:
        return "text"

    return None


def looks_like_json(content: str):
    stripped = content.strip()
    return (
        stripped.startswith("{")
        and stripped.endswith("}")
    ) or (
        stripped.startswith("[")
        and stripped.endswith("]")
    )


def looks_like_csv(content: str):
    lines = content.splitlines()

    if len(lines) < 2:
        return False

    first_line = lines[0]
    second_line = lines[1]

    return "," in first_line and "," in second_line


def preview_data_reference(protocol: str, uri: str):
    protocol = (protocol or "").lower().strip()

    if protocol == "inline":
        return decode_inline_reference(uri)

    if protocol == "file":
        return preview_file_reference(uri)

    if protocol in {"http", "https"}:
        return preview_http_reference(uri)

    if protocol == "s3":
        return {
            "kind": "s3",
            "available": False,
            "uri": uri,
            "message": (
                "S3 artifact preview is not yet configured. "
                "This protocol is reserved for future object-storage integration."
            ),
        }

    if protocol == "artifact":
        return {
            "kind": "artifact",
            "available": False,
            "uri": uri,
            "message": (
                "Orchestrator-managed artifact preview is not yet implemented. "
                "This will be used for portable artifact IDs such as "
                "artifact://workflow/task/output."
            ),
        }

    if protocol == "grpc":
        return {
            "kind": "grpc",
            "available": False,
            "uri": uri,
            "message": (
                "gRPC DataReference preview is not directly supported in the portal. "
                "Expose previewable outputs through inline, HTTP, S3, or artifact references."
            ),
        }

    return {
        "kind": protocol or "unknown",
        "available": False,
        "uri": uri,
        "message": f"Preview not implemented for protocol: {protocol}",
    }