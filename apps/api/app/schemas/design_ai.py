from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Edit(StrictModel):
    kind: Literal["rename", "describe", "set_run_input", "set_node_label", "set_node_parameters"]
    # For run inputs value is JSON text; it is parsed and schema-validated server-side.
    value: str = Field(max_length=16000)
    node_id: str | None


class AssistantTurn(StrictModel):
    message: str = Field(min_length=1, max_length=5000)
    template_key: Literal["denmark", "dutch", "portugal", "germany"] | None
    expected_revision: int | None
    edits: list[Edit] = Field(max_length=10)


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
    template_key: Literal["denmark", "dutch", "portugal", "germany"]
    guided: bool = False


class GuidedSettingsRequest(RevisionRequest):
    seed: int
