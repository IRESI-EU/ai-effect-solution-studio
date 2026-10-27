import re
from datetime import datetime
from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ContractStatus = Literal["draft", "active", "deprecated", "withdrawn"]
SourceKind = Literal["manual", "manifest", "wp3_package", "demo"]
ValueRepresentation = Literal["data_reference", "inline_value", "structured_object"]
SourceRequirement = Literal[
    "upstream_operation",
    "workflow_input",
    "upstream_or_workflow_input",
    "none",
]
OperationRole = Literal[
    "source",
    "transformer",
    "analyzer",
    "model",
    "reporter",
    "adapter",
    "sink",
    "other",
]

SEMANTIC_VERSION_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
URN_PATTERN = re.compile(
    r"^urn:"
    r"[A-Za-z0-9][A-Za-z0-9-]{0,30}[A-Za-z0-9]:"
    r"[A-Za-z0-9._~!$&'()*+,;=:@/?#%+-]+$",
    re.IGNORECASE,
)
URI_SCHEME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*$")
HEX_DIGITS = frozenset("0123456789abcdefABCDEF")


def _validate_non_blank_entries(values: list[str], field_name: str) -> list[str]:
    normalized = [value.strip() for value in values]
    if any(not value for value in normalized):
        raise ValueError(f"{field_name} must not contain blank entries")
    return normalized


def _has_valid_percent_escapes(value: str) -> bool:
    index = 0
    while index < len(value):
        if value[index] != "%":
            index += 1
            continue
        if (
            index + 2 >= len(value)
            or value[index + 1] not in HEX_DIGITS
            or value[index + 2] not in HEX_DIGITS
        ):
            return False
        index += 3
    return True


class StrictContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CardinalityMixin(StrictContractModel):
    min_cardinality: int = Field(default=0, ge=0)
    max_cardinality: int | None = Field(default=1, ge=0)

    @model_validator(mode="after")
    def validate_cardinality(self):
        if (
            self.max_cardinality is not None
            and self.max_cardinality < self.min_cardinality
        ):
            raise ValueError(
                "max_cardinality must be null or greater than or equal to min_cardinality"
            )
        return self


class ContractSlotBase(CardinalityMixin):
    name: str = Field(min_length=1)
    semantic_concept: str = Field(min_length=1)
    value_representation: ValueRepresentation
    data_reference_protocols: list[str] = Field(default_factory=list)
    content_types: list[str] = Field(default_factory=list)
    schema_ref: str | None = None
    compatibility_notes: list[str] = Field(default_factory=list)

    @field_validator("name", "semantic_concept")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be blank")
        return normalized

    @field_validator("schema_ref")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("data_reference_protocols")
    @classmethod
    def validate_protocols(cls, values: list[str]) -> list[str]:
        return _validate_non_blank_entries(values, "data_reference_protocols")

    @field_validator("content_types")
    @classmethod
    def validate_content_types(cls, values: list[str]) -> list[str]:
        return _validate_non_blank_entries(values, "content_types")


class OperationContractInput(ContractSlotBase):
    required: bool
    source_requirement: SourceRequirement

    @model_validator(mode="after")
    def validate_input_logic(self):
        if self.required and self.min_cardinality < 1:
            raise ValueError("required inputs must have min_cardinality of at least one")
        if not self.required and self.min_cardinality != 0:
            raise ValueError("optional inputs must have min_cardinality zero")
        if self.required and self.source_requirement == "none":
            raise ValueError("required inputs must declare a source requirement")
        if self.source_requirement == "none" and self.min_cardinality > 0:
            raise ValueError(
                "inputs with source_requirement 'none' cannot require a value"
            )
        return self


class OperationContractOutput(ContractSlotBase):
    pass


class ParameterDefinition(StrictContractModel):
    type: Literal["integer", "number", "boolean", "string"]
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=1000)
    required: bool = False
    default: Any = None
    minimum: float | None = None
    maximum: float | None = None
    enum: list[Any] | None = None

    @model_validator(mode="after")
    def supported_definition(self):
        from app.services.parameter_values import effective_parameters
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("minimum must not exceed maximum")
        if self.type == "string" and not self.enum:
            raise ValueError("String execution parameters must declare an enumeration")
        spec = self.model_dump(exclude_none=True)
        if "default" in self.model_fields_set:
            spec["default"] = self.default
            effective_parameters({"properties": {"value": spec}}, {})
        if self.enum is not None:
            if not self.enum:
                raise ValueError("enum must not be empty")
            for value in self.enum:
                effective_parameters({"properties": {"value": spec}}, {"value": value})
        return self


class ExecutionParameterContract(StrictContractModel):
    schema_version: Literal["1.0"] = "1.0"
    transport: Literal["http-parameters-v1"] = "http-parameters-v1"
    properties: dict[str, ParameterDefinition] = Field(default_factory=dict, max_length=30)

    @field_validator("properties")
    @classmethod
    def safe_names(cls, value):
        if any(not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", name) for name in value):
            raise ValueError("Parameter names must be lowercase identifiers")
        return value


class OperationContractDefinition(StrictContractModel):
    operation_role: OperationRole
    inputs: list[OperationContractInput] = Field(default_factory=list)
    outputs: list[OperationContractOutput] = Field(default_factory=list)
    adapter_capabilities: list[dict[str, Any]] = Field(default_factory=list)
    compatibility_notes: list[str] = Field(default_factory=list)
    execution_parameters: ExecutionParameterContract | None = None

    @model_validator(mode="after")
    def validate_unique_slot_names(self):
        input_names = [slot.name for slot in self.inputs]
        if len(input_names) != len(set(input_names)):
            raise ValueError("input slot names must be unique")

        output_names = [slot.name for slot in self.outputs]
        if len(output_names) != len(set(output_names)):
            raise ValueError("output slot names must be unique")

        return self


class OperationContractWrite(StrictContractModel):
    operation_identity: str
    runtime_operation_name: str = Field(min_length=1)
    contract_version: str
    schema_version: str = "1.0"
    source_kind: SourceKind = "manual"
    source_reference: str | None = None
    definition: OperationContractDefinition

    @field_validator("operation_identity")
    @classmethod
    def validate_operation_identity(cls, value: str) -> str:
        normalized = value.strip()
        if (
            not normalized
            or any(character.isspace() or ord(character) < 32 or ord(character) == 127 for character in normalized)
            or not _has_valid_percent_escapes(normalized)
        ):
            raise ValueError("operation_identity must be a valid URI or URN")

        try:
            parsed = urlsplit(normalized)
            if parsed.netloc:
                parsed.port
        except ValueError as exc:
            raise ValueError("operation_identity must be a valid URI or URN") from exc

        if parsed.scheme.lower() == "urn":
            if not URN_PATTERN.fullmatch(normalized):
                raise ValueError("operation_identity must be a valid URI or URN")
            return normalized

        if (
            not parsed.scheme
            or not URI_SCHEME_PATTERN.fullmatch(parsed.scheme)
            or not (parsed.netloc or parsed.path)
            or (
                parsed.scheme.lower() in {"http", "https"}
                and (not parsed.netloc or not parsed.hostname)
            )
        ):
            raise ValueError("operation_identity must be a valid URI or URN")
        return normalized

    @field_validator("runtime_operation_name")
    @classmethod
    def validate_runtime_operation_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("runtime_operation_name must not be blank")
        return normalized

    @field_validator("contract_version")
    @classmethod
    def validate_contract_version(cls, value: str) -> str:
        normalized = value.strip()
        if not SEMANTIC_VERSION_PATTERN.fullmatch(normalized):
            raise ValueError("contract_version must use semantic-version syntax")
        return normalized

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: str) -> str:
        if value != "1.0":
            raise ValueError("schema_version must equal '1.0'")
        return value

    @field_validator("source_reference")
    @classmethod
    def normalize_source_reference(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class OperationContractCreate(OperationContractWrite):
    pass


class OperationContractUpdate(OperationContractWrite):
    pass


class OperationContractRead(OperationContractWrite):
    model_config = ConfigDict(from_attributes=True)

    id: str
    service_id: str
    status: ContractStatus
    created_at: datetime
    updated_at: datetime
    activated_at: datetime | None = None
    deprecated_at: datetime | None = None
    withdrawn_at: datetime | None = None


class OperationContractResolution(StrictContractModel):
    resolution: Literal["active", "unknown"]
    reason: Literal["no_active_contract"] | None
    contract: OperationContractRead | None
