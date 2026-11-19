"""Closed exercise actual rejected output; no repair or provider call."""
import json
from pathlib import Path
import pytest
from pydantic import ValidationError
from app.schemas.solution_assistant import SavedSolutionResponse

def test_actual_empty_revision_is_rejected_without_inventing_edits():
    value=json.loads((Path(__file__).parent/'fixtures/complete-journey-rejected-j2-20261119.json').read_text(encoding='utf-8'))
    assert value['outcome']=='proposal' and value['solution_edits']==[]
    with pytest.raises(ValidationError,match='Only a proposal contains one or more solution edits'):
        SavedSolutionResponse.model_validate(value)
