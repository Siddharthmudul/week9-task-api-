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


def test_profile_requires_authentication(client):
    unauthorized = client.get("/api/users/me")
    assert unauthorized.status_code == 401
    assert unauthorized.get_json() == {
        "status": "error",
        "message": "Missing or invalid token",
    }
    registered = client.post(
        "/api/auth/register",
        json={"username": "reader", "email": "reader@example.com", "password": "strong-password"},
    )
    token = registered.get_json()["data"]["access_token"]
    response = client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.get_json()["data"]["username"] == "reader"


def test_versioned_api_path_remains_available(client):
    registered = client.post(
        "/api/v1/auth/register",
        json={"name": "legacy_user", "email": "legacy@example.com", "password": "strong-password"},
    )
    assert registered.status_code == 201
    assert registered.get_json()["data"]["user"]["username"] == "legacy_user"


def test_api_root_returns_available_endpoints(client):
    response = client.get("/")
    assert response.status_code == 302
    assert response.headers["Location"] == "/docs"


def test_docs_page_renders_documentation_in_browser(client):
    response = client.get("/docs")
    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert b"Task Management API" in response.data
    assert b"/api/auth/register" in response.data
    assert b"/api/tasks" in response.data
    assert b'"total_items": 48' in response.data


def test_documentation_files_are_available(client):
    response = client.get("/docs/files/swagger.yaml")
    assert response.status_code == 200
    assert b"openapi: 3.0.3" in response.data