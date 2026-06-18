from sqlalchemy.orm import Session
from app.models.service import Service
from app.schemas.wp3_import import WP3ImportRequest


def import_wp3_package(payload: WP3ImportRequest, db: Session):
    blueprint = payload.blueprint
    dockerinfo = payload.dockerinfo

    docker_entries = {
        item["container_name"]: item
        for item in dockerinfo.get("docker_info_list", [])
    }

    nodes = blueprint.get("nodes", [])

    incoming_by_target = {}
    outgoing_by_source = {}

    for node in nodes:
        source_container = node.get("container_name", "")
        operation_info = node.get("operation_signature_list", [{}])[0]

        for connection in operation_info.get("connected_to", []):
            target_container = connection.get("container_name", "")

            outgoing_by_source.setdefault(source_container, []).append(target_container)
            incoming_by_target.setdefault(target_container, []).append(source_container)

    imported_services = []

    for node in nodes:
        container_name = node.get("container_name", "")
        operation_info = node.get("operation_signature_list", [{}])[0]
        operation_signature = operation_info.get("operation_signature", {})

        docker_entry = docker_entries.get(container_name, {})

        operation_name = operation_signature.get("operation_name", "")
        input_message = operation_signature.get("input_message_name", "Request")
        output_message = operation_signature.get("output_message_name", "Response")

        service_id = f"svc-imported-{container_name}-{operation_name}".lower().replace("_", "-")

        has_incoming = container_name in incoming_by_target
        has_outgoing = container_name in outgoing_by_source

        if not has_incoming:
            input_type = "Workflow Start"
        else:
            input_type = f"{container_name} Input"

        if not has_outgoing:
            output_type = "Workflow Output"
        else:
            first_target = outgoing_by_source[container_name][0]
            output_type = f"{first_target} Input"

        service = Service(
            id=service_id,
            name=f"{container_name} / {operation_name}",
            provider=payload.provider,
            category=payload.category,
            status="pending_review",
            version=blueprint.get("version", "1.0"),
            description=f"Imported from WP3 blueprint {blueprint.get('name', 'Unnamed blueprint')}.",
            input_type=input_type,
            output_type=output_type,
            trust_badge=payload.trust_badge,
            container_name=container_name,
            image=node.get("image", ""),
            proto_uri=node.get("proto_uri", ""),
            node_type=node.get("node_type", "MLModel"),
            operation_name=operation_name,
            input_message_name=input_message,
            output_message_name=output_message,
            internal_host=docker_entry.get("ip_address", container_name),
            internal_port=str(docker_entry.get("port", "8080")),
        )

        db.merge(service)
        imported_services.append(service)

    db.commit()

    return {
        "imported_count": len(imported_services),
        "services": [
            {
                "id": service.id,
                "name": service.name,
                "container_name": service.container_name,
                "operation_name": service.operation_name,
                "input_type": service.input_type,
                "output_type": service.output_type,
            }
            for service in imported_services
        ],
    }