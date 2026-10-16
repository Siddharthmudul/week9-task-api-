import pytest

from app import create_app
from app.extensions import db
from config import TestingConfig


@pytest.fixture()
def client():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def register(client, email="person@example.com", password="correct-horse"):
    return client.post(
        "/api/auth/register",
        json={"username": "test_person", "email": email, "password": password},
    )


def test_register_login_refresh_and_logout(client):
    response = register(client)
    assert response.status_code == 201
    data = response.get_json()["data"]
    assert data["message"] == "User registered successfully"
    assert data["user"]["username"] == "test_person"
    assert data["user"]["email"] == "person@example.com"
    assert data["user"]["created_at"].endswith("Z")

    login = client.post(
        "/api/auth/login",
        json={"email": "PERSON@example.com", "password": "correct-horse"},
    )
    assert login.status_code == 200
    tokens = login.get_json()["data"]
    refreshed = client.post(
        "/api/auth/refresh",
        headers={"Authorization": f"Bearer {tokens['refresh_token']}"},
    )
    assert refreshed.status_code == 200
    access = tokens["access_token"]
    logged_out = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {access}"})
    assert logged_out.status_code == 200
    assert client.get("/api/users/me", headers={"Authorization": f"Bearer {access}"}).status_code == 401


def test_registration_validation_and_duplicate_email(client):
    invalid = client.post("/api/auth/register", json={})
    assert invalid.status_code == 400
    assert invalid.get_json() == {
        "status": "error",
        "message": "Validation failed",
        "errors": {
            "username": ["Username must be 3-30 characters using letters, numbers, or underscores"],
            "email": ["Must be a valid email address"],
            "password": ["Must be between 8 and 128 characters"],
        },
    }
    assert register(client).status_code == 201
    duplicate = register(client, email="PERSON@example.com")
    assert duplicate.status_code == 409


def test_password_reset_uses_email_and_rejects_reset_token_as_access(client, monkeypatch):
    register(client)
    captured = {}
    monkeypatch.setattr(
        "app.auth.routes.send_password_reset_email",
        lambda user, token: captured.update(token=token),
    )
    response = client.post(    "/api/auth/password-reset/request", json={"email": "person@example.com"})
    assert response.status_code == 200
    assert "token" in captured
    denied = client.get("/api/users/me", headers={"Authorization": f"Bearer {captured['token']}"})
    assert denied.status_code == 401
    reset = client.post(
        "/api/auth/password-reset/confirm",
        json={"token": captured["token"], "password": "new-correct-password"},
    )
    assert reset.status_code == 200
    reused = client.post(
        "/api/auth/password-reset/confirm",
        json={"token": captured["token"], "password": "another-correct-password"},
    )
    assert reused.status_code == 400
    assert client.post(
        "/api/auth/login",
        json={"email": "person@example.com", "password": "new-correct-password"},
    ).status_code == 200