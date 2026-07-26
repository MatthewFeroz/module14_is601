"""Integration coverage for authenticated calculation BREAD endpoints."""

from uuid import uuid4


def register_and_login(client, label: str) -> dict[str, str]:
    unique = uuid4().hex[:10]
    username = f"{label}_{unique}"
    password = "SecurePass123!"
    registration = client.post(
        "/register",
        json={
            "first_name": "Calculation",
            "last_name": "Tester",
            "username": username,
            "email": f"{username}@example.com",
            "password": password,
            "confirm_password": password,
        },
    )
    assert registration.status_code == 201

    login = client.post(
        "/login",
        json={"identifier": username, "password": password},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_calculation_routes_require_a_valid_jwt(client):
    assert client.get("/calculations").status_code == 401
    assert client.get("/insights").status_code == 401
    assert client.get(
        "/calculations",
        headers={"Authorization": "Bearer invalid.jwt.token"},
    ).status_code == 401


def test_complete_bread_lifecycle_persists_correct_values(client):
    headers = register_and_login(client, "bread")

    created = client.post(
        "/calculations",
        headers=headers,
        json={"type": "multiplication", "inputs": [3, 4]},
    )
    assert created.status_code == 201
    calculation_id = created.json()["id"]
    assert created.json()["result"] == 12

    browsed = client.get("/calculations", headers=headers)
    assert browsed.status_code == 200
    assert [record["id"] for record in browsed.json()] == [calculation_id]

    read = client.get(
        f"/calculations/{calculation_id}",
        headers=headers,
    )
    assert read.status_code == 200
    assert read.json()["inputs"] == [3, 4]

    edited = client.put(
        f"/calculations/{calculation_id}",
        headers=headers,
        json={"inputs": [5, 6]},
    )
    assert edited.status_code == 200
    assert edited.json()["inputs"] == [5, 6]
    assert edited.json()["result"] == 30

    deleted = client.delete(
        f"/calculations/{calculation_id}",
        headers=headers,
    )
    assert deleted.status_code == 204
    assert client.get(
        f"/calculations/{calculation_id}",
        headers=headers,
    ).status_code == 404
    assert client.get("/calculations", headers=headers).json() == []


def test_user_cannot_read_edit_or_delete_another_users_record(client):
    owner_headers = register_and_login(client, "owner")
    other_headers = register_and_login(client, "other")
    created = client.post(
        "/calculations",
        headers=owner_headers,
        json={"type": "addition", "inputs": [7, 8]},
    )
    calculation_id = created.json()["id"]

    assert client.get(
        f"/calculations/{calculation_id}",
        headers=other_headers,
    ).status_code == 404
    assert client.put(
        f"/calculations/{calculation_id}",
        headers=other_headers,
        json={"inputs": [1, 2]},
    ).status_code == 404
    assert client.delete(
        f"/calculations/{calculation_id}",
        headers=other_headers,
    ).status_code == 404


def test_invalid_inputs_are_rejected_without_corrupting_record(client):
    headers = register_and_login(client, "invalid")

    division_by_zero = client.post(
        "/calculations",
        headers=headers,
        json={"type": "division", "inputs": [20, 0]},
    )
    assert division_by_zero.status_code == 422
    assert "Cannot divide by zero" in division_by_zero.text

    created = client.post(
        "/calculations",
        headers=headers,
        json={"type": "division", "inputs": [20, 2]},
    )
    calculation_id = created.json()["id"]
    invalid_edit = client.put(
        f"/calculations/{calculation_id}",
        headers=headers,
        json={"inputs": [20, 0]},
    )
    assert invalid_edit.status_code == 400
    assert invalid_edit.json()["detail"] == "Cannot divide by zero."
    unchanged = client.get(
        f"/calculations/{calculation_id}",
        headers=headers,
    )
    assert unchanged.json()["inputs"] == [20, 2]
    assert unchanged.json()["result"] == 10


def test_insights_include_only_authenticated_users_records(client):
    owner_headers = register_and_login(client, "insight_owner")
    other_headers = register_and_login(client, "insight_other")

    for payload in (
        {"type": "addition", "inputs": [4, 6]},
        {"type": "multiplication", "inputs": [3, 5]},
    ):
        assert client.post(
            "/calculations",
            headers=owner_headers,
            json=payload,
        ).status_code == 201
    assert client.post(
        "/calculations",
        headers=other_headers,
        json={"type": "addition", "inputs": [100, 200]},
    ).status_code == 201

    insights = client.get("/insights", headers=owner_headers)
    assert insights.status_code == 200
    body = insights.json()
    assert body["total_calculations"] == 2
    assert body["average_result"] == 12.5
    assert body["highest_result"] == 15
    assert body["latest_activity"] is not None
    assert body["operation_counts"] == {
        "addition": 1,
        "subtraction": 0,
        "multiplication": 1,
        "division": 0,
    }
