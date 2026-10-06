from uuid import uuid4

from app.models.deployment import Deployment
from app.models.solution import Solution


def register_user(client, *, email: str, role: str, node: str | None = None):
    return client.post(
        "/auth/register",
        json={
            "display_name": "Research User",
            "email": email,
            "password": "ResearchPassword123",
            "requested_role": role,
            "node": node,
        },
    )


def approve_user(admin_client, user: dict, *, role: str | None = None, node: str | None = None):
    return admin_client.post(
        f"/admin/users/{user['id']}/approve",
        json={"role": role or user["role"], "node": node if node is not None else user["node"]},
    )


def test_registration_requires_admin_approval(client, anonymous_client):
    email = f"pending-{uuid4().hex[:8]}@example.org"
    registration = register_user(
        anonymous_client,
        email=email,
        role="node_manager",
        node="portugal",
    )
    assert registration.status_code == 201
    assert registration.json()["status"] == "pending"

    pending_login = anonymous_client.post(
        "/auth/login", json={"email": email, "password": "ResearchPassword123"}
    )
    assert pending_login.status_code == 403

    approval = approve_user(client, registration.json())
    assert approval.status_code == 200
    assert approval.json()["status"] == "active"

    login = anonymous_client.post(
        "/auth/login", json={"email": email, "password": "ResearchPassword123"}
    )
    assert login.status_code == 200
    assert login.json()["node"] == "portugal"


def test_dutch_node_code_is_accepted(client, anonymous_client):
    email = f"dutch-{uuid4().hex[:8]}@example.org"
    registration = register_user(
        anonymous_client,
        email=email,
        role="node_manager",
        node="dutch",
    )

    assert registration.status_code == 201
    assert registration.json()["node"] == "dutch"
    assert approve_user(client, registration.json()).status_code == 200

    login = anonymous_client.post(
        "/auth/login", json={"email": email, "password": "ResearchPassword123"}
    )
    assert login.status_code == 200
    assert login.json()["node"] == "dutch"


def test_node_manager_cannot_manage_another_nodes_service(client, anonymous_client):
    users = []
    for node in ("portugal", "germany"):
        registration = register_user(
            anonymous_client,
            email=f"{node}-{uuid4().hex[:8]}@example.org",
            role="node_manager",
            node=node,
        )
        assert registration.status_code == 201
        assert approve_user(client, registration.json()).status_code == 200
        users.append((node, registration.json()))

    portugal_client = anonymous_client
    login = portugal_client.post(
        "/auth/login",
        json={"email": users[0][1]["email"], "password": "ResearchPassword123"},
    )
    assert login.status_code == 200
    service = portugal_client.post(
        "/services",
        json={
            "name": "Owned PT service",
            "provider": "Portuguese Node",
            "category": "Test",
            "description": "Ownership boundary test",
            "input_type": "JSON",
            "output_type": "JSON",
        },
    )
    assert service.status_code == 200
    assert service.json()["owner_node"] == "portugal"

    portugal_client.post("/auth/logout")
    german_login = portugal_client.post(
        "/auth/login",
        json={"email": users[1][1]["email"], "password": "ResearchPassword123"},
    )
    assert german_login.status_code == 200
    forbidden = portugal_client.put(f"/services/{service.json()['id']}/archive")
    assert forbidden.status_code == 403


def test_solution_designer_only_sees_owned_solutions(client, anonymous_client):
    registered = []
    for index in range(2):
        registration = register_user(
            anonymous_client,
            email=f"designer-{index}-{uuid4().hex[:8]}@example.org",
            role="solution_designer",
        )
        assert registration.status_code == 201
        assert approve_user(client, registration.json()).status_code == 200
        registered.append(registration.json())

    first_client = anonymous_client
    first_client.post(
        "/auth/login",
        json={"email": registered[0]["email"], "password": "ResearchPassword123"},
    )
    created = first_client.post(
        "/solutions",
        json={"name": "Private solution", "nodes": [], "edges": [], "status": "draft"},
    )
    assert created.status_code == 200
    first_client.post("/auth/logout")

    first_client.post(
        "/auth/login",
        json={"email": registered[1]["email"], "password": "ResearchPassword123"},
    )
    assert first_client.get("/solutions").json() == []
    assert first_client.get(f"/solutions/{created.json()['id']}").status_code == 403


def test_solution_designer_cannot_publish_services(client, anonymous_client):
    registration = register_user(
        anonymous_client,
        email=f"designer-publish-{uuid4().hex[:8]}@example.org",
        role="solution_designer",
    )
    assert approve_user(client, registration.json()).status_code == 200
    anonymous_client.post(
        "/auth/login",
        json={"email": registration.json()["email"], "password": "ResearchPassword123"},
    )
    response = anonymous_client.post(
        "/services",
        json={
            "name": "Forbidden service",
            "provider": "Example",
            "category": "Test",
            "description": "Should not be created",
            "input_type": "JSON",
            "output_type": "JSON",
        },
    )
    assert response.status_code == 403


def test_admin_can_preserve_and_assign_legacy_solution_with_deployments(
    client, anonymous_client, session_factory
):
    solution_id = str(uuid4())
    deployment_id = str(uuid4())
    with session_factory() as db:
        db.add(
            Solution(
                id=solution_id,
                name="Existing builder design",
                description="Created before user accounts",
                nodes=[],
                edges=[],
                status="draft",
                created_by_user_id=None,
            )
        )
        db.add(
            Deployment(
                id=deployment_id,
                workflow_id=f"legacy-{uuid4().hex}",
                solution_id=solution_id,
                name="Existing deployment",
                status="completed",
                created_by_user_id=None,
            )
        )
        db.commit()

    registration = register_user(
        anonymous_client,
        email=f"legacy-owner-{uuid4().hex[:8]}@example.org",
        role="solution_designer",
    )
    assert approve_user(client, registration.json()).status_code == 200

    unassigned = client.get("/admin/ownership/unassigned")
    assert unassigned.status_code == 200
    assert solution_id in {item["id"] for item in unassigned.json()["solutions"]}

    assignment = client.post(
        f"/admin/ownership/solutions/{solution_id}/assign",
        json={"user_id": registration.json()["id"], "include_unowned_deployments": True},
    )
    assert assignment.status_code == 200
    assert assignment.json()["linked_deployments"] == 1

    anonymous_client.post(
        "/auth/login",
        json={"email": registration.json()["email"], "password": "ResearchPassword123"},
    )
    assert anonymous_client.get(f"/solutions/{solution_id}").status_code == 200
    assert anonymous_client.get(f"/deployments/{deployment_id}").status_code == 200


def test_password_change_revokes_sessions_and_replaces_password(client, anonymous_client):
    email = f"password-change-{uuid4().hex[:8]}@example.org"
    registration = register_user(
        anonymous_client,
        email=email,
        role="solution_designer",
    )
    assert registration.status_code == 201
    assert approve_user(client, registration.json()).status_code == 200

    login = anonymous_client.post(
        "/auth/login",
        json={"email": email, "password": "ResearchPassword123"},
    )
    assert login.status_code == 200

    changed = anonymous_client.post(
        "/auth/change-password",
        json={
            "current_password": "ResearchPassword123",
            "new_password": "UpdatedResearchPassword456",
        },
    )
    assert changed.status_code == 204
    assert anonymous_client.get("/auth/me").status_code == 401

    old_password = anonymous_client.post(
        "/auth/login",
        json={"email": email, "password": "ResearchPassword123"},
    )
    assert old_password.status_code == 401

    new_password = anonymous_client.post(
        "/auth/login",
        json={"email": email, "password": "UpdatedResearchPassword456"},
    )
    assert new_password.status_code == 200
