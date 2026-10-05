import base64
import csv
import json
import os
from pathlib import Path
from urllib.parse import quote, urlparse

import requests


MAX_TEXT_PREVIEW_CHARS = 5000
MAX_CSV_ROWS = 20
HTTP_TIMEOUT_SECONDS = 10
MAX_SVG_BYTES = 2 * 1024 * 1024
MAX_REMOTE_PREVIEW_BYTES = 5 * 1024 * 1024
GRPC_PREVIEW_TARGETS = {
    "grid_synth_service:50051": "http://grid_synth_service:8080",
    "benchmark-runner:50051": "http://benchmark-runner:8080",
}


def artifact_roots() -> list[Path]:
    """Return the configured read-only roots used to resolve node /data paths."""
    configured = [os.getenv("ARTIFACT_BASE_PATH", "/wp3-artifacts")]
    configured.extend(os.getenv("ARTIFACT_BASE_PATHS", "").split(","))

    roots: list[Path] = []
    for value in configured:
        value = value.strip()
        if not value:
            continue
        root = Path(value).resolve()
        if root not in roots:
            roots.append(root)
    return roots


def resolve_artifact_file(uri: str) -> Path | None:
    """Resolve a file URI only when it belongs to a configured artifact root."""
    source = Path(uri)
    if not source.is_absolute():
        return None

    roots = artifact_roots()
    if source.parts[:2] == ("/", "data"):
        relative_parts = source.parts[2:]
        for root in roots:
            candidate = root.joinpath(*relative_parts).resolve()
            if candidate.is_relative_to(root) and candidate.is_file():
                return candidate
        return None

    path = source.resolve()
    if any(path.is_relative_to(root) for root in roots) and path.is_file():
        return path
    return None


def preview_svg_file(uri: str):
    source = Path(uri)
    if not source.is_absolute() or source.suffix.lower() != ".svg":
        return {"kind": "svg", "available": False, "message": "Invalid SVG artifact path."}
    path = resolve_artifact_file(uri)
    if path is None:
        return {"kind": "svg", "available": False, "message": "SVG artifact is not available in the shared artifact volume."}
    if path.stat().st_size > MAX_SVG_BYTES:
        return {"kind": "svg", "available": False, "message": "SVG exceeds the 2 MiB preview limit."}
    content = path.read_bytes()
    # SVGs are displayed as images, never injected into the page as markup.
    if b"<svg" not in content[:2048].lower() or b"<!doctype" in content.lower() or b"<!entity" in content.lower():
        return {"kind": "svg", "available": False, "message": "Invalid SVG artifact."}
    return {
        "kind": "svg", "available": True, "format": "svg", "content_type": "image/svg+xml",
        "uri": uri, "image_data_url": "data:image/svg+xml;base64," + base64.b64encode(content).decode("ascii"),
    }


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
    if Path(uri).suffix.lower() == ".svg":
        return preview_svg_file(uri)
    path = resolve_artifact_file(uri)

    if path is None:
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
        format_hint=Path(uri).suffix.lower().replace(".", ""),
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


def preview_grpc_reference(uri: str, task_id: str | None):
    """Bridge approved Dutch gRPC references to their private control-data API."""
    base_url = GRPC_PREVIEW_TARGETS.get(uri)
    if not base_url:
        return {
            "kind": "grpc",
            "available": False,
            "uri": uri,
            "message": "This gRPC output does not have an approved portal preview bridge.",
        }
    if not task_id:
        return {
            "kind": "grpc",
            "available": False,
            "uri": uri,
            "message": "The workflow task identifier is required to preview this gRPC result.",
        }

    preview_url = f"{base_url}/control/data/{quote(task_id, safe='')}"
    try:
        response = requests.get(preview_url, timeout=HTTP_TIMEOUT_SECONDS)
        response.raise_for_status()
        if len(response.content) > MAX_REMOTE_PREVIEW_BYTES:
            return {
                "kind": "grpc",
                "available": False,
                "uri": uri,
                "message": "The Dutch node result exceeds the 5 MiB portal preview limit.",
            }
    except Exception as exc:
        return {
            "kind": "grpc",
            "available": False,
            "uri": uri,
            "message": f"Could not fetch the Dutch node result: {exc}",
        }

    content_type = response.headers.get("content-type", "application/json")
    return parse_content_preview(
        content=response.text,
        format_hint=infer_format_from_uri_or_content_type(preview_url, content_type) or "json",
        source_uri=f"grpc://{uri}/{task_id}",
        kind="grpc",
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


def preview_data_reference(protocol: str, uri: str, task_id: str | None = None):
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
        return preview_grpc_reference(uri, task_id)

    return {
        "kind": protocol or "unknown",
        "available": False,
        "uri": uri,
        "message": f"Preview not implemented for protocol: {protocol}",
    }
