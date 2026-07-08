from pydantic import BaseModel


class WorkflowSubmitNode(BaseModel):
    node_id: str
    service_id: str | None = None
    container_name: str
    proto_uri: str | None = None
    image: str | None = None
    node_type: str | None = None
    operation_name: str
    input_message_name: str | None = None
    output_message_name: str | None = None
    internal_host: str | None = None
    internal_port: str | None = None


class WorkflowSubmitEdge(BaseModel):
    source: str
    target: str


class WorkflowSubmitRequest(BaseModel):
    name: str
    solution_id: str | None = None
    nodes: list[WorkflowSubmitNode]
    edges: list[WorkflowSubmitEdge]