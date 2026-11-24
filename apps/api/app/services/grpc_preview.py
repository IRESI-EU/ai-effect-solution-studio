"""Preview gRPC outputs of catalogue services using their stored .proto files.

WP3 services that exchange data over gRPC return a DataReference such as
``{"protocol": "grpc", "uri": "pb-report-generator:50051", "format": "GenerateReport"}``.
Downstream services fetch the data by calling that RPC with an empty request.
The portal does the same, so it can show the result as JSON:

1. The target host must belong to an approved catalogue service. Arbitrary
   hosts are never contacted.
2. The service's .proto (stored at import time under SERVICE_CONTRACT_PATH)
   is compiled at runtime. The RPC named in ``format``, or else the service's
   operation, is called with an empty request.
3. The response message is converted to JSON.

Most WP3 services hold only their latest result, so the preview shows what
the service returns now, which may come from a later run.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.service import Service

GRPC_TIMEOUT_SECONDS = 10
MAX_GRPC_MESSAGE_BYTES = 5 * 1024 * 1024


class GrpcPreviewError(Exception):
    pass


def _host_of(uri: str) -> str:
    value = uri.removeprefix("grpc://").split("/", 1)[0]
    return value.rsplit(":", 1)[0] if ":" in value else value


def find_catalogue_service(db: Session, uri: str) -> Service | None:
    host = _host_of(uri)
    if not host:
        return None
    return (
        db.query(Service)
        .filter(Service.status == "approved")
        .filter(or_(Service.internal_host == host, Service.container_name == host))
        .first()
    )


def stored_proto_path(service: Service) -> Path | None:
    root = Path(settings.service_contract_path).resolve()
    for candidate in (service.proto_uri, service.contract_uri):
        if not candidate:
            continue
        path = Path(candidate)
        if not path.is_absolute():
            path = root / candidate
        try:
            path = path.resolve()
        except OSError:
            continue
        if path.is_file() and path.suffix == ".proto" and root in path.parents:
            return path
    return None


def _load_descriptors(proto_path: Path):
    """Compile a .proto (and its sibling imports) into a descriptor pool."""
    from google.protobuf import descriptor_pb2, descriptor_pool
    from grpc_tools import protoc

    import grpc_tools

    well_known = Path(grpc_tools.__file__).parent / "_proto"
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "set.pb")
        code = protoc.main([
            "protoc",
            f"-I{proto_path.parent}",
            f"-I{well_known}",
            "--include_imports",
            f"--descriptor_set_out={out}",
            str(proto_path),
        ])
        if code != 0:
            raise GrpcPreviewError(f"The service's proto file could not be compiled ({proto_path.name}).")
        file_set = descriptor_pb2.FileDescriptorSet()
        file_set.ParseFromString(Path(out).read_bytes())

    pool = descriptor_pool.DescriptorPool()
    for file_proto in file_set.file:
        pool.Add(file_proto)
    main_file = pool.FindFileByName(proto_path.name)
    return pool, main_file


def _find_method(main_file, method_name: str):
    for service in main_file.services_by_name.values():
        method = service.methods_by_name.get(method_name)
        if method is not None:
            return method
    return None


def call_grpc_method(target: str, proto_path: Path, method_name: str) -> dict:
    import grpc
    from google.protobuf import json_format, message_factory

    _, main_file = _load_descriptors(proto_path)
    method = _find_method(main_file, method_name)
    if method is None:
        raise GrpcPreviewError(f"The service's proto does not define an RPC named '{method_name}'.")
    if method.client_streaming or method.server_streaming:
        raise GrpcPreviewError("Streaming gRPC outputs cannot be previewed yet.")

    request_cls = message_factory.GetMessageClass(method.input_type)
    response_cls = message_factory.GetMessageClass(method.output_type)
    path = f"/{method.containing_service.full_name}/{method.name}"

    with grpc.insecure_channel(
        target, options=[("grpc.max_receive_message_length", MAX_GRPC_MESSAGE_BYTES)]
    ) as channel:
        call = channel.unary_unary(
            path,
            request_serializer=lambda message: message.SerializeToString(),
            response_deserializer=response_cls.FromString,
        )
        response = call(request_cls(), timeout=GRPC_TIMEOUT_SECONDS)

    try:
        # Show zero/false/empty fields too (e.g. "anomalies_detected": 0).
        return json_format.MessageToDict(
            response, preserving_proto_field_name=True, always_print_fields_with_no_presence=True
        )
    except TypeError:  # protobuf < 5.26
        return json_format.MessageToDict(
            response, preserving_proto_field_name=True, including_default_value_fields=True
        )


def preview_catalogue_grpc(db: Session, uri: str, method_hint: str | None) -> dict | None:
    """Return a preview, or None when no catalogue service matches the host."""
    service = find_catalogue_service(db, uri)
    if service is None:
        return None

    base = {"kind": "grpc", "uri": uri, "service_name": service.name}
    proto_path = stored_proto_path(service)
    if proto_path is None:
        return {
            **base,
            "available": False,
            "message": (
                f"{service.name} has no stored .proto file, so its gRPC output cannot be decoded. "
                "Re-import the service from its WP3 package to enable previews."
            ),
        }

    method_name = (method_hint or service.operation_name or "").strip()
    target = uri.removeprefix("grpc://").split("/", 1)[0]
    try:
        content = call_grpc_method(target, proto_path, method_name)
    except GrpcPreviewError as exc:
        return {**base, "available": False, "message": str(exc)}
    except Exception as exc:  # grpc.RpcError and connection failures
        details = getattr(exc, "details", None)
        message = details() if callable(details) else str(exc)
        return {**base, "available": False, "message": f"Could not read the gRPC result from {service.name}: {message}"}

    return {
        **base,
        "available": True,
        "kind": "json",
        "source_kind": "grpc",
        "content": content,
        "note": f"Decoded from {method_name} on {target}. The service returns its most recent result.",
    }
