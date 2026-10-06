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
