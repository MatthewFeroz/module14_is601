from uuid import uuid4

from sqlalchemy import select

from app.database import SessionLocal
from app.models import User
from app.security import decode_access_token, verify_password


def registration_payload():
    unique = uuid4().hex[:10]
    return {
        "first_name": "Grace",
        "last_name": "Hopper",
        "username": f"grace_{unique}",
        "email": f"grace.{unique}@example.com",
        "password": "CompilerPass13!",
        "confirm_password": "CompilerPass13!",
    }


def test_register_hashes_password_and_rejects_duplicates(client):
    payload = registration_payload()
    response = client.post("/register", json=payload)

    assert response.status_code == 201
    assert response.json()["message"] == "Registration successful"
    assert "password" not in response.text

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == payload["email"]))
        assert user is not None
        assert user.password_hash != payload["password"]
        assert verify_password(payload["password"], user.password_hash)

    duplicate = client.post(
        "/register",
        json={**registration_payload(), "email": payload["email"].upper()},
    )
    assert duplicate.status_code == 400
    assert "already exists" in duplicate.json()["detail"]


def test_login_returns_jwt_for_email_and_protects_profile(client):
    payload = registration_payload()
    assert client.post("/register", json=payload).status_code == 201

    login = client.post(
        "/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login.status_code == 200
    token_data = login.json()
    assert token_data["token_type"] == "bearer"
    assert decode_access_token(token_data["access_token"])["sub"] == token_data["user"]["id"]

    profile = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token_data['access_token']}"},
    )
    assert profile.status_code == 200
    assert profile.json()["email"] == payload["email"]


def test_wrong_password_and_missing_token_are_unauthorized(client):
    payload = registration_payload()
    assert client.post("/register", json=payload).status_code == 201

    wrong_password = client.post(
        "/login",
        json={"username": payload["username"], "password": "IncorrectPass13!"},
    )
    assert wrong_password.status_code == 401
    assert wrong_password.json()["detail"] == "Invalid email, username, or password"

    missing_token = client.get("/auth/me")
    invalid_token = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert missing_token.status_code == 401
    assert invalid_token.status_code == 401
