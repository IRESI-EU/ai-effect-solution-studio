from typing import Literal
import math

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Edit(StrictModel):
    kind: Literal["rename", "describe", "set_run_input", "set_node_label", "set_node_parameters", "append_bound_operation"]
    # For run inputs value is JSON text; it is parsed and schema-validated server-side.
    value: str = Field(max_length=16000)
    node_id: str | None


class DiscoveryDecision(StrictModel):
    outcome: Literal["clarification_needed", "supported_recommendation", "no_supported_match"]
    candidate_id: str | None = Field(default=None, max_length=100)
    question: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def consistent_outcome(self):
        if (self.outcome == "supported_recommendation") != bool(self.candidate_id) or (self.outcome != "supported_recommendation" and self.candidate_id is not None):
            raise ValueError("Only recommendations select one advertised candidate")
        if (self.outcome == "clarification_needed") != bool(self.question and self.question.strip()) or (self.outcome != "clarification_needed" and self.question is not None):
            raise ValueError("Only clarification contains a non-empty question")
        return self


class SettingAssignment(StrictModel):
    name: str = Field(min_length=1, max_length=64)
    value: str | int | float | bool

    @model_validator(mode="after")
    def finite_value(self):
        if isinstance(self.value, float) and not math.isfinite(self.value):
            raise ValueError("Settings must contain finite numbers")
        return self


class CompositionSettings(StrictModel):
    first: list[SettingAssignment] = Field(default_factory=list, max_length=8)
    second: list[SettingAssignment] = Field(default_factory=list, max_length=8)


class AssistantTurn(StrictModel):
    message: str = Field(min_length=1, max_length=5000)
    template_key: str | None = Field(max_length=80)
    expected_revision: int | None
    edits: list[Edit] = Field(max_length=10)
    recommended_seed: Literal[42, 43] | None = None
    discovery: DiscoveryDecision | None = None
    composition_settings: CompositionSettings | None = None


class ChatRequest(StrictModel):
    message: str = Field(min_length=1, max_length=4000)
    draft_id: str | None = None
    revision: int | None = None
    # History is context only. It never supplies authorization or executable state.
    history: list[dict[str, str]] = Field(default_factory=list, max_length=12)


class RevisionRequest(StrictModel):
    revision: int = Field(ge=0)


class ApplyRequest(RevisionRequest):
    proposal_id: str


class StartRequest(StrictModel):
    template_key: str | None = Field(default=None, max_length=80)
    candidate_id: str | None = Field(default=None, max_length=100)
    guided: bool = False
    recommended_seed: Literal[42, 43] | None = None
    recommendation_revision: str | None = None
    composition_settings: CompositionSettings | None = None
    creation_request_id: str | None = Field(default=None, max_length=36)

    @model_validator(mode="after")
    def one_creation_path(self):
        if bool(self.template_key) == bool(self.candidate_id):
            raise ValueError("Select one registered recommendation or legacy template")
        if self.candidate_id and not self.recommendation_revision:
            raise ValueError("Creation requires the reviewed recommendation revision")
        return self


class GuidedSettingsRequest(RevisionRequest):
    seed: int
