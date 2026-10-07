def test_onboarding_request_preserves_runtime_evidence(client):
    manifest = {
        "schema_version": "1.0",
        "service": {
            "id": "service-onboarding-evidence-test",
            "name": "Onboarding Evidence Test",
            "provider": "German Node",
            "category": "Test",
            "version": "1.0.0",
            "description": "Test service onboarding evidence.",
        },
        "runtime": {
            "type": "docker",
            "container_name": "onboarding-evidence-test",
            "image": "example.invalid/onboarding-evidence-test:1.0.0",
            "internal_port": "8080",
            "health_path": "/health",
        },
        "interface": {
            "type": "control",
            "operation_name": "RunTest",
            "input_type": "Test Input",
            "output_type": "Test Output",
            "contract_uri": "ai-effect.service.json",
        },
        "orchestration": {"mode": "native"},
    }
    onboarding = {
        "source_type": "public_git",
        "source_revision": "0123456789abcdef",
        "runtime_status": "already_running",
        "revision_pinned": True,
        "image_reviewed": True,
        "secrets_external": True,
        "health_verified": False,
        "registration_only_acknowledged": True,
    }

    response = client.post(
        "/services/import/confirm-manual",
        json={
            "repo_url": "https://github.com/example/service",
            "branch": "0123456789abcdef",
            "manifest_path": "ai-effect.service.json",
            "manifest": manifest,
            "onboarding": onboarding,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "pending_review"
    assert payload["interface_contract"]["onboarding"] == onboarding


def test_manual_preview_preserves_unknown_fields_and_interface_errors(client):
    manifest = {
        "schema_version": "1.0",
        "service": {
            "id": "service-preview-lossless-test",
            "name": "Lossless Preview Test",
            "provider": "Portuguese Node",
            "category": "Test",
        },
        "runtime": {
            "container_name": "lossless-preview-test",
            "image": "example.invalid/lossless:1.0.0",
        },
        "interface": {
            "type": "http",
            "operation_name": "Predict",
            "input_type": "Input DataReference",
            "output_type": "Output DataReference",
            "http": {"method": "POST"},
        },
        "orchestration": {"mode": "sidecar"},
        "provider_extension": {"must_survive": True},
    }

    response = client.post(
        "/services/import/preview-manual",
        json={
            "repo_url": "provider-supplied",
            "branch": "unversioned",
            "manifest_path": "ai-effect.service.json",
            "manifest": manifest,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "invalid"
    assert payload["raw_manifest"]["provider_extension"] == {"must_survive": True}
    assert any("HTTP field 'path' is required" in item["message"] for item in payload["validation"])


def test_duplicate_onboarding_request_remains_blocked_and_pending(client):
    manifest = {
        "schema_version": "1.0",
        "service": {
            "id": "service-duplicate-onboarding-test",
            "name": "Duplicate Onboarding Test",
            "provider": "Danish Node",
            "category": "Test",
            "description": "Verifies duplicate onboarding protection.",
        },
        "runtime": {
            "container_name": "duplicate-onboarding-test",
            "image": "example.invalid/duplicate:1.0.0",
        },
        "interface": {
            "type": "control",
            "operation_name": "Run",
            "input_type": "Input DataReference",
            "output_type": "Output DataReference",
        },
        "orchestration": {"mode": "native"},
    }
    request = {
        "repo_url": "provider-supplied",
        "branch": "unversioned",
        "manifest_path": "ai-effect.service.json",
        "manifest": manifest,
        "onboarding": {
            "source_type": "manual_manifest",
            "runtime_status": "needs_deployment",
            "registration_only_acknowledged": True,
        },
    }

    created = client.post("/services/import/confirm-manual", json=request)
    duplicate = client.post("/services/import/confirm-manual", json=request)

    assert created.status_code == 200
    assert created.json()["status"] == "pending_review"
    assert created.json()["trust_badge"] == "pending_review"
    assert duplicate.status_code == 409
    assert "already exists" in duplicate.json()["detail"]


def test_public_git_preview_route_passes_exact_manifest_location(client, monkeypatch):
    captured = {}

    def fake_preview_service_manifest(*, repo_url, branch, manifest_path):
        captured.update(repo_url=repo_url, branch=branch, manifest_path=manifest_path)
        return {
            "status": "invalid",
            "raw_manifest": {},
            "service": None,
            "validation": [{"level": "error", "message": "test response"}],
        }

    monkeypatch.setattr("app.main.preview_service_manifest", fake_preview_service_manifest)
    response = client.post(
        "/services/import/preview",
        json={
            "repo_url": "https://github.com/example/service",
            "branch": "0123456789abcdef",
            "manifest_path": "manifests/ai-effect.service.json",
        },
    )

    assert response.status_code == 200
    assert captured == {
        "repo_url": "https://github.com/example/service",
        "branch": "0123456789abcdef",
        "manifest_path": "manifests/ai-effect.service.json",
    }
