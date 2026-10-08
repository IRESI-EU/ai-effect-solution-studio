import hashlib
import io
import json
import re
import shutil
import stat
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.service import Service
from app.models.solution import Solution
from app.models.user import User
from app.schemas.service_import import (
    PackageConnection,
    PackageImportConfirmRequest,
    PackageImportConfirmResponse,
    PackageImportPreviewResponse,
    PackageOperation,
    PackageServicePreview,
)
from app.services.audit import record_audit_event
from app.services.runtime_preflight import build_runtime_health_url


MAX_ARCHIVE_BYTES = 25 * 1024 * 1024
MAX_EXPANDED_BYTES = 100 * 1024 * 1024
MAX_MEMBER_BYTES = 5 * 1024 * 1024
MAX_FILES = 256
SERVICE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,119}$")


class PackageImportError(ValueError):
    pass


@dataclass
class ParsedPackage:
    name: str
    digest: str
    services: list[dict]
    connections: list[dict]
    proto_files: dict[str, bytes]
    warnings: list[str]


def preview_package(archive_name: str, archive: bytes, db: Session, user: User):
    parsed = parse_package(archive)
    token = uuid4().hex
    staging = contract_root() / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    (staging / f"{token}.zip").write_bytes(archive)
    (staging / f"{token}.json").write_text(
        json.dumps({"owner_user_id": user.id, "archive_name": archive_name, "digest": parsed.digest}),
        encoding="utf-8",
    )

    services = []
    compatibility = "verified"
    for item in parsed.services:
        proposed_id = f"pkg-{slug(item['container_name'])}-{parsed.digest[:10]}"
        conflicts = []
        if db.query(Service).filter(Service.id == proposed_id).first():
            conflicts.append(f"Service ID '{proposed_id}' already exists. Repeat uploads never overwrite records.")
        logical_conflict = db.query(Service).filter(
            Service.container_name == item["container_name"],
            Service.version == item["version"],
        ).first()
        if logical_conflict:
            conflicts.append(
                f"Logical service '{item['container_name']}' version '{item['version']}' already exists as '{logical_conflict.id}'."
            )
        operations = [PackageOperation(**operation) for operation in item["operations"]]
        selected = operations[0].operation_name if len(operations) == 1 else None
        blockers = list(item["blockers"])
        if len(operations) > 1:
            blockers.append("Select one supported operation explicitly; the catalogue currently stores one operation per service record.")
            compatibility = "needs_selection"
        if any(not operation.compatible_with_proto for operation in operations) or not operations:
            compatibility = "blocked"
        services.append(
            PackageServicePreview(
                key=item["container_name"], proposed_id=proposed_id,
                name=item["container_name"].replace("_", " ").title(),
                description=f"Imported from {parsed.name}", category=item["node_type"],
                version=item["version"], container_name=item["container_name"],
                image=item["image"], internal_host=item["internal_host"],
                internal_port=item["internal_port"], node_type=item["node_type"],
                proto_path=item["proto_path"], operations=operations,
                selected_operation=selected, duplicate_conflicts=conflicts, blockers=blockers,
            )
        )

    return PackageImportPreviewResponse(
        upload_token=token, package_name=parsed.name, archive_name=archive_name,
        services=services,
        connections=[PackageConnection(**connection) for connection in parsed.connections],
        warnings=parsed.warnings,
        registration_status="blocked" if all(s.blockers or s.duplicate_conflicts for s in services) else "preview",
        operation_compatibility=compatibility,
    )


def confirm_package(request: PackageImportConfirmRequest, db: Session, user: User):
    if not request.registration_only_acknowledged:
        raise HTTPException(422, "Confirm that registration does not deploy or activate services.")
    archive_path, metadata_path, metadata = staged_upload(request.upload_token, user)
    parsed = parse_package(archive_path.read_bytes())
    selected = {item.key: item for item in request.services if item.selected}
    if not selected:
        raise HTTPException(422, "Select at least one service.")
    parsed_by_key = {item["container_name"]: item for item in parsed.services}
    if set(selected) - set(parsed_by_key):
        raise HTTPException(422, "The confirmation contains a service that was not present in the uploaded package.")

    selected_edges = []
    unresolved_edges = []
    for edge in parsed.connections:
        source_selected = edge["source_service"] in selected
        target_selected = edge["target_service"] in selected
        if source_selected and target_selected:
            selected_edges.append(edge)
        elif source_selected or target_selected:
            unresolved_edges.append(edge)
    if request.create_solution and unresolved_edges:
        raise HTTPException(422, "A draft solution cannot be created because selected services leave unresolved package connections.")

    final_id = uuid4().hex
    pending_dir = contract_root() / ".pending" / final_id
    final_dir = contract_root() / "packages" / final_id
    created_services = []
    try:
        validate_confirmation(selected, parsed_by_key, db)
        pending_proto = pending_dir / "microservice"
        pending_proto.mkdir(parents=True, exist_ok=False)
        for relative, content in parsed.proto_files.items():
            target = pending_dir / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)

        for key, choice in selected.items():
            source = parsed_by_key[key]
            operation = next(op for op in source["operations"] if op["operation_name"] == choice.operation_name)
            runtime_host = (choice.internal_host or source["internal_host"] or "").strip()
            runtime_port = (choice.internal_port or source["internal_port"] or "").strip()
            incomplete = not runtime_host or not runtime_port
            if incomplete and not choice.register_incomplete_draft:
                raise HTTPException(422, f"{key}: runtime host and port are required, or explicitly register it as an incomplete draft.")
            if not incomplete:
                candidate = Service(internal_host=runtime_host, internal_port=runtime_port, health_path=choice.health_path)
                _, address_error = build_runtime_health_url(candidate)
                if address_error:
                    raise HTTPException(422, f"{key}: {address_error}")

            durable_proto = str(final_dir / source["proto_path"])
            evidence = {
                "source_type": "wp3_zip", "package_digest": parsed.digest,
                "archive_name": metadata["archive_name"], "declared_runtime_unverified": True,
                "all_operations": source["operations"], "selected_operation": choice.operation_name,
                "runtime_verification": {"status": "not_verified", "message": "Imported runtime address is an unverified declaration."},
            }
            service = Service(
                id=choice.service_id, name=choice.name.strip(), provider=user.display_name,
                category=choice.category.strip(), version=source["version"],
                description=choice.description.strip(), status="pending_review",
                trust_badge="pending_review", lifecycle_status="active",
                repository_url=f"package:{metadata['archive_name']}", repository_branch=parsed.digest,
                manifest_path="blueprint.json", interface_type="control",
                interface_contract=evidence, orchestration_mode="native", adapter_type=None,
                health_path=choice.health_path, contract_uri=durable_proto,
                container_name=source["container_name"], image=source["image"], proto_uri=durable_proto,
                node_type=source["node_type"], operation_name=operation["operation_name"],
                input_message_name=operation["input_message_name"], output_message_name=operation["output_message_name"],
                input_type=operation["input_message_name"], output_type=operation["output_message_name"],
                internal_host=runtime_host, internal_port=runtime_port,
                owner_node=user.node, created_by_user_id=user.id,
            )
            db.add(service)
            record_audit_event(db, user, "service.package_imported", "service", service.id, {
                "package_digest": parsed.digest, "container_name": service.container_name,
                "operation_name": service.operation_name, "runtime_unverified": True,
            })
            created_services.append(service)

        solution = None
        if request.create_solution:
            solution = Solution(
                id=str(uuid4()), name=(request.solution_name or parsed.name).strip(),
                description=f"Draft imported from {metadata['archive_name']}", status="draft",
                nodes=[{"id": key, "service_id": choice.service_id, "container_name": key, "operation_name": choice.operation_name, "node_type": parsed_by_key[key]["node_type"]} for key, choice in selected.items()],
                edges=[{"source": edge["source_service"], "target": edge["target_service"]} for edge in selected_edges],
                created_by_user_id=user.id,
            )
            db.add(solution)
            record_audit_event(db, user, "solution.package_imported", "solution", solution.id, {"package_digest": parsed.digest})

        db.flush()
        final_dir.parent.mkdir(parents=True, exist_ok=True)
        pending_dir.replace(final_dir)
        db.commit()
        archive_path.unlink(missing_ok=True)
        metadata_path.unlink(missing_ok=True)
        return PackageImportConfirmResponse(
            services=[{"id": item.id, "name": item.name, "status": item.status} for item in created_services],
            solution={"id": solution.id, "name": solution.name, "status": solution.status} if solution else None,
            message=f"Registered {len(created_services)} service(s) for administrator review.",
        )
    except HTTPException:
        db.rollback()
        shutil.rmtree(pending_dir, ignore_errors=True)
        shutil.rmtree(final_dir, ignore_errors=True)
        raise
    except Exception as exc:
        db.rollback()
        shutil.rmtree(pending_dir, ignore_errors=True)
        shutil.rmtree(final_dir, ignore_errors=True)
        raise HTTPException(500, f"Package confirmation failed without persisting records: {exc}") from exc


def parse_package(archive: bytes) -> ParsedPackage:
    if not archive or len(archive) > MAX_ARCHIVE_BYTES:
        raise PackageImportError("ZIP archive must be non-empty and no larger than 25 MiB.")
    digest = hashlib.sha256(archive).hexdigest()
    try:
        source = zipfile.ZipFile(io.BytesIO(archive))
    except zipfile.BadZipFile as exc:
        raise PackageImportError("The uploaded file is not a valid ZIP archive.") from exc
    infos = [item for item in source.infolist() if not item.is_dir()]
    if not infos or len(infos) > MAX_FILES:
        raise PackageImportError(f"Archive must contain between 1 and {MAX_FILES} files.")
    total = 0
    names = []
    for info in infos:
        path = PurePosixPath(info.filename.replace("\\", "/"))
        if "\\" in info.filename or path.is_absolute() or ".." in path.parts or not path.parts:
            raise PackageImportError(f"Unsafe archive path: {info.filename}")
        if stat.S_ISLNK(info.external_attr >> 16):
            raise PackageImportError(f"Symbolic links are not allowed: {info.filename}")
        if info.file_size > MAX_MEMBER_BYTES:
            raise PackageImportError(f"Archive member exceeds 5 MiB: {info.filename}")
        total += info.file_size
        if total > MAX_EXPANDED_BYTES:
            raise PackageImportError("Expanded archive exceeds 100 MiB.")
        names.append(path)

    blueprints = [path for path in names if path.name == "blueprint.json"]
    dockerinfos = [path for path in names if path.name == "dockerinfo.json"]
    if len(blueprints) != 1 or len(dockerinfos) != 1:
        raise PackageImportError("Package must contain exactly one blueprint.json and one dockerinfo.json.")
    root = blueprints[0].parent
    if len(root.parts) > 1 or dockerinfos[0].parent != root:
        raise PackageImportError("Required files must be at the archive root or inside one enclosing folder.")
    proto_paths = [path for path in names if path.parent == root / "microservice" and path.suffix.lower() == ".proto"]
    if not proto_paths:
        raise PackageImportError("Package must contain microservice/*.proto definitions.")

    def read_json(path):
        try:
            value = json.loads(source.read(str(path)).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PackageImportError(f"{path.name} is not valid UTF-8 JSON.") from exc
        if not isinstance(value, dict):
            raise PackageImportError(f"{path.name} must contain a JSON object.")
        return value

    blueprint = read_json(blueprints[0])
    dockerinfo = read_json(dockerinfos[0])
    if blueprint.get("type") != "pipeline-topology/v2" or not isinstance(blueprint.get("nodes"), list):
        raise PackageImportError("blueprint.json must use pipeline-topology/v2 and contain a nodes array.")
    if not isinstance(dockerinfo.get("docker_info_list"), list):
        raise PackageImportError("dockerinfo.json must contain a docker_info_list array.")
    docker_by_name = {item.get("container_name"): item for item in dockerinfo["docker_info_list"] if isinstance(item, dict)}
    proto_files = {str(path.relative_to(root)): source.read(str(path)) for path in proto_paths}
    try:
        proto_text = {path: content.decode("utf-8", errors="strict") for path, content in proto_files.items()}
    except UnicodeDecodeError as exc:
        raise PackageImportError("Protobuf definitions must be UTF-8 text files.") from exc
    services = []
    connections = []
    seen = set()
    for node in blueprint["nodes"]:
        if not isinstance(node, dict):
            raise PackageImportError("Every blueprint node must be an object.")
        container = clean(node.get("container_name"))
        image = clean(node.get("image"))
        proto_path = clean(node.get("proto_uri"))
        if not container or not image or not proto_path or container in seen:
            raise PackageImportError("Every node needs unique container_name plus image and proto_uri values.")
        seen.add(container)
        normalized_proto = str(PurePosixPath(proto_path))
        if normalized_proto not in proto_text:
            raise PackageImportError(f"{container}: referenced protobuf '{proto_path}' is missing from the package.")
        operations = []
        for entry in node.get("operation_signature_list") or []:
            signature = entry.get("operation_signature") if isinstance(entry, dict) else None
            if not isinstance(signature, dict):
                continue
            operation = clean(signature.get("operation_name"))
            input_name = clean(signature.get("input_message_name"))
            output_name = clean(signature.get("output_message_name"))
            compatible = bool(operation and input_name and output_name and proto_supports(proto_text[normalized_proto], operation, input_name, output_name))
            operations.append({
                "operation_name": operation, "input_message_name": input_name,
                "output_message_name": output_name, "compatible_with_proto": compatible,
                "compatibility_message": "Operation and message names match the uploaded protobuf." if compatible else "Operation or exact input/output message names are missing or do not match the uploaded protobuf.",
            })
            for target in entry.get("connected_to") or []:
                if not isinstance(target, dict):
                    continue
                target_signature = target.get("operation_signature") or {}
                if target.get("container_name") and target_signature.get("operation_name"):
                    connections.append({"source_service": container, "source_operation": operation, "target_service": str(target["container_name"]), "target_operation": str(target_signature["operation_name"])})
        blockers = []
        if not operations:
            blockers.append("No operation signatures were supplied for this service.")
        elif any(not item["compatible_with_proto"] for item in operations):
            blockers.append("At least one declared operation is incompatible with its uploaded protobuf definition.")
        runtime = docker_by_name.get(container) or {}
        services.append({
            "container_name": container, "image": image, "node_type": clean(node.get("node_type")) or "MLModel",
            "version": clean(node.get("version")) or version_from_image(image), "proto_path": normalized_proto,
            "internal_host": clean(runtime.get("ip_address")) or None, "internal_port": clean(runtime.get("port")) or None,
            "operations": operations, "blockers": blockers,
        })
    unknown_connections = [edge for edge in connections if edge["target_service"] not in seen]
    if unknown_connections:
        raise PackageImportError("A pipeline connection references a service that is not present in blueprint.json.")
    operations_by_service = {
        item["container_name"]: {operation["operation_name"] for operation in item["operations"]}
        for item in services
    }
    invalid_connections = [
        edge for edge in connections
        if edge["source_operation"] not in operations_by_service.get(edge["source_service"], set())
        or edge["target_operation"] not in operations_by_service.get(edge["target_service"], set())
    ]
    if invalid_connections:
        raise PackageImportError("A pipeline connection references an operation that is not declared by its service.")
    extras = [str(path) for path in names if path not in {blueprints[0], dockerinfos[0], *proto_paths}]
    warnings = [f"Ignored {len(extras)} non-contract package file(s)."] if extras else []
    return ParsedPackage(clean(blueprint.get("name")) or "Imported WP3 package", digest, services, connections, proto_files, warnings)


def validate_confirmation(selected, parsed_by_key, db):
    ids = []
    for key, choice in selected.items():
        if not SERVICE_ID_RE.fullmatch(choice.service_id):
            raise HTTPException(422, f"{key}: service ID must be 3-120 lowercase letters, digits, dots, underscores, or hyphens.")
        if not choice.name.strip() or not choice.description.strip() or not choice.category.strip():
            raise HTTPException(422, f"{key}: catalogue name, description, and category are required.")
        operations = parsed_by_key[key]["operations"]
        matching = [item for item in operations if item["operation_name"] == choice.operation_name]
        if len(matching) != 1 or not matching[0]["compatible_with_proto"]:
            raise HTTPException(422, f"{key}: select exactly one protobuf-compatible operation.")
        ids.append(choice.service_id)
    if len(ids) != len(set(ids)):
        raise HTTPException(422, "Selected service IDs must be unique.")
    existing = [row[0] for row in db.query(Service.id).filter(Service.id.in_(ids)).all()]
    if existing:
        raise HTTPException(409, f"Existing service records were not changed: {', '.join(existing)}")
    for key in selected:
        source = parsed_by_key[key]
        existing_logical = db.query(Service).filter(
            Service.container_name == source["container_name"],
            Service.version == source["version"],
        ).first()
        if existing_logical:
            raise HTTPException(
                409,
                f"Existing logical service was not changed: {source['container_name']} version {source['version']} ({existing_logical.id})",
            )


def staged_upload(token: str, user: User):
    if not re.fullmatch(r"[a-f0-9]{32}", token):
        raise HTTPException(404, "Package preview not found.")
    staging = contract_root() / "staging"
    archive_path, metadata_path = staging / f"{token}.zip", staging / f"{token}.json"
    if not archive_path.is_file() or not metadata_path.is_file():
        raise HTTPException(404, "Package preview expired or was not found. Upload it again.")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("owner_user_id") != user.id:
        raise HTTPException(403, "This package preview belongs to another user.")
    return archive_path, metadata_path, metadata


def contract_root():
    root = Path(settings.service_contract_path).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def proto_supports(content: str, operation: str, input_name: str, output_name: str):
    pattern = rf"\brpc\s+{re.escape(operation)}\s*\(\s*(?:stream\s+)?{re.escape(input_name)}\s*\)\s*returns\s*\(\s*(?:stream\s+)?{re.escape(output_name)}\s*\)"
    return re.search(pattern, content, flags=re.MULTILINE) is not None


def version_from_image(image: str):
    tail = image.rsplit("/", 1)[-1]
    return tail.rsplit(":", 1)[1] if ":" in tail else "1.0.0"


def slug(value: str):
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:70] or "service"


def clean(value):
    return str(value).strip() if value is not None else ""
