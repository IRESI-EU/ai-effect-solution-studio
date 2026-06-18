import base64
import csv
from pathlib import Path


def decode_inline_reference(uri: str):
    decoded = base64.b64decode(uri).decode("utf-8")
    return {
        "kind": "inline",
        "content": decoded,
    }


def preview_file_reference(uri: str):
    path = Path(uri)

    if not path.exists():
        return {
            "kind": "file",
            "available": False,
            "message": f"File is not directly available to the portal API: {uri}",
            "uri": uri,
        }

    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
            reader = csv.DictReader(f)
            rows = []
            for index, row in enumerate(reader):
                if index >= 20:
                    break
                rows.append(row)

        return {
            "kind": "csv",
            "available": True,
            "uri": uri,
            "columns": reader.fieldnames or [],
            "rows": rows,
        }

    content = path.read_text(encoding="utf-8", errors="replace")

    return {
        "kind": "file",
        "available": True,
        "uri": uri,
        "content": content[:5000],
    }


def preview_data_reference(protocol: str, uri: str):
    if protocol == "inline":
        return decode_inline_reference(uri)

    if protocol == "file":
        return preview_file_reference(uri)

    return {
        "kind": protocol,
        "available": False,
        "message": f"Preview not yet implemented for protocol: {protocol}",
        "uri": uri,
    }