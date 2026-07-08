from pydantic import BaseModel


class ServiceCreate(BaseModel):
    name: str
    provider: str
    category: str
    description: str
    input_type: str
    output_type: str
    version: str = "0.1.0"

    container_name: str = ""
    image: str = ""
    proto_uri: str = ""
    node_type: str = "MLModel"
    operation_name: str = ""
    input_message_name: str = "Request"
    output_message_name: str = "Response"
    internal_host: str = ""
    internal_port: str = "8080"
    lifecycle_status: str = "active"


class ServiceRead(ServiceCreate):
    id: str
    status: str
    trust_badge: str
    description: str | None = None
    lifecycle_status: str = "active"