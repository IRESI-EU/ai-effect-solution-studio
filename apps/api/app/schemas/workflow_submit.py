from pydantic import BaseModel, ConfigDict
from typing import Any


class WorkflowSubmitNode(BaseModel):
    model_config = ConfigDict(extra="forbid")
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
    configuration: dict[str, Any] | None = None


class WorkflowSubmitEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str
    target: str


class WorkflowSubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    solution_id: str | None = None
    expected_updated_at: str | None = None
    nodes: list[WorkflowSubmitNode]
    edges: list[WorkflowSubmitEdge]
    # Optional JSON object supplied at run time to the workflow's start nodes.
    run_input: dict | None = None
