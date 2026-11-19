"""Requests bind conversation proposals to the normal saved solution version."""
from typing import Annotated, Literal
from pydantic import ConfigDict, Field, model_validator
from app.schemas.design_ai import AssistantTurn, DiscoveryDecision, SolutionEdit, StrictModel


class SavedSolutionResponse(StrictModel):
    """Model-only contract. No creation, legacy template or execution authority."""
    model_config = ConfigDict(extra='forbid', strict=True, revalidate_instances='always')
    outcome: Literal['answer', 'clarification', 'proposal', 'unsupported']
    message: str = Field(min_length=1, max_length=5000)
    clarification: str | None = Field(max_length=500)
    solution_edits: list[SolutionEdit] = Field(max_length=10)
    assumptions: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(max_length=4)

    @model_validator(mode='after')
    def consistent_outcome(self):
        if not self.message.strip():
            raise ValueError('A response requires a useful message')
        if self.outcome == 'clarification':
            if not self.clarification or not self.clarification.strip():
                raise ValueError('Clarification requires one focused question')
        elif self.clarification is not None:
            raise ValueError('Only clarification may contain a question')
        if (self.outcome == 'proposal') != bool(self.solution_edits):
            raise ValueError('Only a proposal contains one or more solution edits')
        if self.assumptions and self.outcome != 'proposal':
            raise ValueError('Only a reviewed proposal may contain proposed assumptions')
        if any(not assumption.strip() for assumption in self.assumptions):
            raise ValueError('Disclose each proposed assumption clearly')
        return self


def as_assistant_turn(response: SavedSolutionResponse) -> AssistantTurn:
    """Explicit adapter into the existing candidate/review engine, after validation."""
    response = SavedSolutionResponse.model_validate(response)
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
