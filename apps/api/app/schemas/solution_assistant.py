"""Requests bind conversation proposals to the normal saved solution version."""
from pydantic import Field
from app.schemas.design_ai import StrictModel


class SolutionRevisionRequest(StrictModel):
    expected_updated_at: str
    conversation_revision: int = Field(ge=0)


class SolutionChatRequest(SolutionRevisionRequest):
    message: str = Field(min_length=1, max_length=4000)


class SolutionProposalRequest(SolutionRevisionRequest):
    proposal_id: str
