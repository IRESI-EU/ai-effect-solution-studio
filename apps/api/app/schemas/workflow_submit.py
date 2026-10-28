from pydantic import BaseModel, ConfigDict, Field
from typing import Any


class OperationContractPin(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contract_id: str = Field(min_length=1)
    contract_version: str = Field(min_length=1)


class SlotBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_slot: str = Field(min_length=1)
    target_slot: str = Field(min_length=1)


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
    operation_contract: OperationContractPin | None = None


class WorkflowSubmitEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str
    target: str
    binding: SlotBinding | None = None


class WorkflowSubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    solution_id: str | None = None
    expected_updated_at: str | None = None
    nodes: list[WorkflowSubmitNode]
    edges: list[WorkflowSubmitEdge]
    # Optional JSON object supplied at run time to the workflow's start nodes.
    run_input: dict | None = None
