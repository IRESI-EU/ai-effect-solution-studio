import json

from app.services import data_reference_service


class PreviewResponse:
    def __init__(self, payload: dict):
        self.content = json.dumps(payload).encode("utf-8")
        self.text = self.content.decode("utf-8")
        self.headers = {"content-type": "application/json"}

    def raise_for_status(self):
        return None


def test_dutch_grpc_reference_uses_allowlisted_control_data_endpoint(monkeypatch):
    requested = []

    def fake_get(url, timeout):
        requested.append((url, timeout))
        return PreviewResponse({"status": "success", "nodes": 174})

    monkeypatch.setattr(data_reference_service.requests, "get", fake_get)
    preview = data_reference_service.preview_data_reference(
        "grpc", "grid_synth_service:50051", "task_60e852c4"
    )

    assert requested == [
        (
            "http://grid_synth_service:8080/control/data/task_60e852c4",
            data_reference_service.HTTP_TIMEOUT_SECONDS,
        )
    ]
    assert preview["available"] is True
    assert preview["kind"] == "json"
    assert preview["content"]["nodes"] == 174


def test_grpc_preview_rejects_unapproved_target(monkeypatch):
    def unexpected_get(*args, **kwargs):
        raise AssertionError("network request must not be attempted")

    monkeypatch.setattr(data_reference_service.requests, "get", unexpected_get)
    preview = data_reference_service.preview_data_reference(
        "grpc", "untrusted-service:50051", "task_demo"
    )

    assert preview["available"] is False
    assert "approved" in preview["message"]
