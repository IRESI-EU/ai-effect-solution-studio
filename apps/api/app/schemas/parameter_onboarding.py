"""Provider review uses the existing parameter contract, never a second validator."""
from typing import Any, Literal

from pydantic import Field

from app.schemas.operation_contract import ParameterDefinition, StrictContractModel


class ParameterDiscoveryRequest(StrictContractModel):
    document: dict[str, Any]
    source_reference: str = Field(min_length=1, max_length=500)
    # OpenAPI must select a real operation; a JSON Schema describes this service's operation.
    operation_id: str | None = Field(default=None, max_length=150)


class ReviewedParameter(StrictContractModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    source_pointer: str = Field(min_length=1, max_length=1000)
    definition: ParameterDefinition
    # Documentary mapping confirmed by the provider, never evaluated as code.
    algorithm_mapping: str = Field(min_length=1, max_length=500)


class ParameterReviewRequest(StrictContractModel):
    discovery_revision: str
    operation_identity: str
    contract_version: str
    operation_role: Literal["source", "transformer", "analyzer", "model", "reporter", "adapter", "sink", "other"] = "other"
    parameters: list[ReviewedParameter] = Field(min_length=1, max_length=30)
    runtime_support_confirmed: bool
    normal_configuration_tested: bool
    invalid_configuration_tested: bool
    evidence_reference: str = Field(default="", max_length=500)


class RuntimeConfirmationRequest(StrictContractModel):
    reviewed_contract_sha256: str
    runtime_support_confirmed: bool
    normal_configuration_tested: bool
    invalid_configuration_tested: bool
    evidence_reference: str = Field(min_length=1, max_length=500)
