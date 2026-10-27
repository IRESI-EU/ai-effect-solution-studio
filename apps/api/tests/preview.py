"""Explicit isolated UI QA harness. Not an application provider or production seed.

Run from repo root with PYTHONPATH=apps/api:
  .venv/Scripts/python.exe apps/api/tests/preview.py
Sign in: designer@example.test / PilotTest12345
All records live only in process memory. Never invokes node workflows.
"""
import uvicorn
import pytest

from conftest import app, environment, settings
from app.schemas.design_ai import AssistantTurn
from app.services.design_ai_provider import get_provider


class PreviewTestProvider:
    async def respond(self, context):
        draft = context.get("draft")
        request = context["request"]
        if not draft:
            return AssistantTurn(message="[TEST PROVIDER · isolated fixtures] The Danish test workflow connects BuildRunConfig to GenerateTopology and RenderTopologies. Create an editable copy to review changes.", template_key="dutch" if "dutch" in request.lower() else "denmark", expected_revision=None, edits=[])
        edits = []
        if "rename" in request.lower():
            edits = [{"kind": "rename", "value": "Energy design study", "node_id": None}]
        return AssistantTurn(message="[TEST PROVIDER · isolated fixtures] " + ("I propose renaming your draft to Energy design study. Review the preview, then select Apply changes." if edits else "This saved test design connects the operations shown in the workflow. Semantic compatibility and live availability remain unverified. Domain edits require verified wrapper inputs."), template_key=None, expected_revision=draft["revision"], edits=edits)


if __name__ == "__main__":
    patches = pytest.MonkeyPatch()
    fixture = environment.__wrapped__(patches)
    next(fixture)
    # Dummy credentials identify a test provider; they are never sent anywhere.
    settings.openai_api_key = "test-only-never-used"
    settings.design_ai_model = "test-provider"
    app.dependency_overrides[get_provider] = lambda: PreviewTestProvider()
    print("ISOLATED UI QA: in-memory fixtures and TEST PROVIDER. No real nodes or external LLM.")
    try:
        uvicorn.run(app, host="127.0.0.1", port=18081)
    finally:
        fixture.close()
        patches.undo()
