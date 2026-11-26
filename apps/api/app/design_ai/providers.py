"""Model providers for Design with AI.

``OpenAICompatibleModel`` talks to any OpenAI-compatible chat endpoint (OpenAI,
or a small model served locally by Ollama / vLLM, by changing the base URL).
``OfflineModel`` composes workflows with simple rules; it needs no network and
is used for tests and when no model is configured.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

import requests

from app.core.config import settings
from app.design_ai.catalogue import ServiceCard, relevance

# Structured-output schema the model must follow. Strict mode needs every
# object closed, so free-form settings are passed as name + JSON string.
RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["reply", "clarifying_question", "workflow"],
    "properties": {
        "reply": {"type": "string"},
        "clarifying_question": {"type": ["string", "null"]},
        "workflow": {
            "anyOf": [
                {"type": "null"},
                {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["steps", "connections"],
                    "properties": {
                        "steps": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["ref", "service_id", "why", "settings"],
                                "properties": {
                                    "ref": {"type": "string"},
                                    "service_id": {"type": "string"},
                                    "why": {"type": "string"},
                                    "settings": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "additionalProperties": False,
                                            "required": ["name", "value_json"],
                                            "properties": {
                                                "name": {"type": "string"},
                                                "value_json": {"type": "string"},
                                            },
                                        },
                                    },
                                },
                            },
                        },
                        "connections": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["from_ref", "to_ref"],
                                "properties": {
                                    "from_ref": {"type": "string"},
                                    "to_ref": {"type": "string"},
                                },
                            },
                        },
                    },
                },
            ]
        },
    },
}


class ModelError(Exception):
    pass


@dataclass
class ModelResult:
    data: dict
    prompt_tokens: int = 0
    completion_tokens: int = 0


class DesignModel(Protocol):
    name: str
    model: str

    def complete(self, messages: list[dict], cards: list[ServiceCard]) -> ModelResult: ...


class OpenAICompatibleModel:
    name = "openai"

    def __init__(self, base_url: str, api_key: str, model: str, timeout: int):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def _body(self, messages: list[dict], response_format: dict) -> dict:
        body = {"model": self.model, "messages": messages, "response_format": response_format}
        # Reasoning models (o-series, gpt-5 family) only accept their default temperature.
        if not self.model.startswith(("o1", "o3", "o4", "gpt-5")):
            body["temperature"] = 0.2
        return body

    def _post(self, messages: list[dict], response_format: dict) -> requests.Response:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=self._body(messages, response_format),
            timeout=self.timeout,
        )

    def complete(self, messages: list[dict], cards: list[ServiceCard]) -> ModelResult:
        return self.complete_json(messages, "workflow_design", RESPONSE_SCHEMA)

    def complete_json(self, messages: list[dict], name: str, schema: dict) -> ModelResult:
        """One chat completion whose answer must follow ``schema`` (strict structured output)."""
        schema_format = {"type": "json_schema", "json_schema": {"name": name, "strict": True, "schema": schema}}
        try:
            response = self._post(messages, schema_format)
            if response.status_code == 400:  # endpoint without structured outputs (some local servers)
                response = self._post(messages, {"type": "json_object"})
        except requests.RequestException as exc:
            raise ModelError(f"The AI model could not be reached: {exc}") from exc
        if response.status_code == 401:
            raise ModelError("The AI model rejected the API key. Check DESIGN_AI_API_KEY.")
        if response.status_code == 429:
            raise ModelError("The AI model is rate limited or out of credit. Try again later.")
        if response.status_code >= 400:
            raise ModelError(f"The AI model returned an error (HTTP {response.status_code}).")
        body = response.json()
        try:
            content = body["choices"][0]["message"]["content"]
            data = json.loads(content)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ModelError("The AI model returned an unreadable answer.") from exc
        usage = body.get("usage") or {}
        return ModelResult(data, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))


class OfflineModel:
    """Rule-based composer: picks the best-matching start service and follows
    compatible outputs to an end service. No network, deterministic."""

    name = "offline"
    model = "rules-v1"

    def complete(self, messages: list[dict], cards: list[ServiceCard]) -> ModelResult:
        request = next((m["content"] for m in reversed(messages) if m["role"] == "user" and not m["content"].startswith("VALIDATION")), "")
        request = request.split("USER REQUEST:", 1)[-1]
        starts = sorted((c for c in cards if c.is_start), key=lambda c: relevance(c, request), reverse=True)
        if not starts or relevance(starts[0], request) == 0:
            return ModelResult({
                "reply": "I could not match your request to services in the catalogue.",
                "clarifying_question": "Which kind of task do you need, for example grid benchmarking, district-heating topologies, time-series generation or synthetic data?",
                "workflow": None,
            })
        chain = [starts[0]]
        while not chain[-1].is_end and len(chain) < 8:
            nxt = [c for c in cards if c.input_type == chain[-1].output_type and c not in chain]
            if not nxt:
                break
            chain.append(max(nxt, key=lambda c: relevance(c, request)))
        steps = [{"ref": f"s{i + 1}", "service_id": c.id, "why": c.purpose, "settings": []} for i, c in enumerate(chain)]
        connections = [{"from_ref": f"s{i + 1}", "to_ref": f"s{i + 2}"} for i in range(len(chain) - 1)]
        names = " → ".join(c.name for c in chain)
        return ModelResult({
            "reply": f"I put together this workflow from the catalogue: {names}. Review it on the canvas and adjust settings before running.",
            "clarifying_question": None,
            "workflow": {"steps": steps, "connections": connections},
        })


def get_model() -> DesignModel:
    if settings.design_ai_provider == "openai":
        return OpenAICompatibleModel(
            settings.design_ai_base_url, settings.design_ai_api_key, settings.design_ai_model, settings.design_ai_timeout_seconds
        )
    return OfflineModel()
