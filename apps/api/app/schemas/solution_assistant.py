"""Requests bind conversation proposals to the normal saved solution version."""
import json
from typing import Annotated, Literal
from pydantic import ConfigDict, Field, model_validator
from app.schemas.design_ai import AssistantTurn, DiscoveryDecision, SolutionEdit, StrictModel


class EditBase(StrictModel):
    """Exact server-supplied base; catalogue identifiers never identify instances."""
    model_config = ConfigDict(extra='forbid', strict=True, revalidate_instances='always')
    kind: Literal['saved', 'pending']
    expected_updated_at: str
    conversation_revision: int = Field(ge=0)
    proposal_id: str | None
    candidate_sha256: str | None

    @model_validator(mode='after')
    def consistent_base(self):
        if self.kind == 'pending':
            if not self.proposal_id or not self.candidate_sha256:
                raise ValueError('Pending edits require the exact current proposal and candidate hash')
        elif self.proposal_id is not None or self.candidate_sha256 is not None:
            raise ValueError('Saved edits cannot identify a pending proposal')
        return self


class RequestedSetting(StrictModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)
    name: str = Field(min_length=1, max_length=300)
    value: bool | int | float | str


class ParameterAction(StrictModel):
    """Interpretation only: application resolves, validates and describes the edit."""
    model_config = ConfigDict(extra='forbid', strict=True)
    operation: Literal['set_parameters']
    target_ref: str = Field(min_length=1, max_length=100)
    requested_values: list[RequestedSetting] = Field(min_length=1, max_length=32)

    @model_validator(mode='after')
    def distinct_names(self):
        names = [value.name for value in self.requested_values]
        if len(names) != len(set(names)):
            raise ValueError('Each requested setting must have one unambiguous value')
        return self


class SavedSolutionResponse(StrictModel):
    """Model-only contract. No creation, legacy template or execution authority."""
    model_config = ConfigDict(extra='forbid', strict=True, revalidate_instances='always')
    outcome: Literal['answer', 'clarification', 'proposal', 'unsupported', 'setting_edit']
    message: str | None = Field(max_length=5000)
    clarification: str | None = Field(max_length=500)
    solution_edits: list[SolutionEdit] = Field(max_length=10)
    edit_base: EditBase | None = Field(default=None, description='Copy an advertised edit base for proposals and setting_edit; null for answers, clarification and unsupported. Use only target_ref values from that base, or unique local_ref for new additions.')
    assumptions: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(max_length=4)
    parameter_action: ParameterAction | None = Field(default=None, description='For setting_edit only: the intended operation, one advertised scoped target and requested values. The application computes before/after and all change prose.')

    @model_validator(mode='after')
    def consistent_outcome(self):
        if self.outcome == 'setting_edit':
            if (self.parameter_action is None or self.edit_base is None or self.message is not None
                    or self.solution_edits or self.assumptions or self.clarification is not None):
                raise ValueError('A setting edit requires only a parameter action and explicit base; no model change summary')
            return self
        if self.parameter_action is not None:
            raise ValueError('Only setting_edit may contain a parameter action')
        if not self.message or not self.message.strip():
            raise ValueError('A response requires a useful message')
        if self.outcome == 'clarification':
            if not self.clarification or not self.clarification.strip():
                raise ValueError('Clarification requires one focused question')
        elif self.clarification is not None:
            raise ValueError('Only clarification may contain a question')
        if (self.outcome == 'proposal') != bool(self.solution_edits):
            raise ValueError('Only a proposal contains one or more solution edits')
        if (self.outcome == 'proposal') != (self.edit_base is not None):
            raise ValueError('Only a proposal requires an explicit saved or pending edit base')
        if self.assumptions and self.outcome != 'proposal':
            raise ValueError('Only a reviewed proposal may contain proposed assumptions')
        if any(not assumption.strip() for assumption in self.assumptions):
            raise ValueError('Disclose each proposed assumption clearly')
        return self


def as_assistant_turn(response: SavedSolutionResponse) -> AssistantTurn:
    """Explicit adapter into the existing candidate/review engine, after validation."""
    response = SavedSolutionResponse.model_validate(response)
    if response.parameter_action is not None:
        action = response.parameter_action
        return AssistantTurn(message='Setting action awaiting application validation.', template_key=None,
            expected_revision=None, edits=[], solution_edits=[SolutionEdit(kind='set_node_parameters',
                node_id=action.target_ref, value=json.dumps({v.name:v.value for v in action.requested_values}, allow_nan=False))])
    discovery = (DiscoveryDecision(outcome='clarification_needed', question=response.clarification)
                 if response.outcome == 'clarification' else None)
    return AssistantTurn(message=response.message, template_key=None, expected_revision=None,
                         edits=[], discovery=discovery, solution_edits=response.solution_edits)


class SolutionRevisionRequest(StrictModel):
    expected_updated_at: str
    conversation_revision: int = Field(ge=0)


class SolutionChatRequest(SolutionRevisionRequest):
    message: str = Field(min_length=1, max_length=4000)


class SolutionProposalRequest(SolutionRevisionRequest):
    proposal_id: str
