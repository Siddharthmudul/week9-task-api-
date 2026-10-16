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


def create_account(client, email, name):
    response = client.post(
        "/api/auth/register",
        json={"username": name.lower(), "email": email, "password": "strong-password"},
    )
    return response.get_json()["data"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_task_crud_filters_pagination_assignment_and_comments(client):
    owner = create_account(client, "owner@example.com", "Owner")
    assignee = create_account(client, "assignee@example.com", "Assignee")
    response = client.post(
        "/api/tasks",
        headers=auth(owner["access_token"]),
        json={
            "title": "Write API docs",
            "description": "Document the task API",
            "priority": "high",
            "status": "in_progress",
            "category": "work",
            "assignee_id": assignee["user"]["id"],
            "due_date": "2026-10-20T12:00:00+00:00",
        },
    )
    assert response.status_code == 201
    task_id = response.get_json()["data"]["id"]

    listing = client.get(
        "/api/tasks?status=in_progress&priority=high&search=docs&page=1&per_page=1",
        headers=auth(assignee["access_token"]),
    )
    assert listing.status_code == 200
    assert listing.get_json()["data"]["pagination"]["total_items"] == 1
    assert listing.get_json()["data"]["pagination"]["per_page"] == 1
    assert set(listing.get_json()["data"]["tasks"][0]) == {
        "id", "title", "description", "status", "priority", "due_date", "created_at", "updated_at"
    }
    assert listing.get_json()["data"]["tasks"][0]["created_at"].endswith("Z")
    assert listing.get_json()["data"]["tasks"][0]["updated_at"].endswith("Z")

    comment = client.post(
        f"/api/tasks/{task_id}/comments",
        headers=auth(assignee["access_token"]),
        json={"body": "I will take this task"},
    )
    assert comment.status_code == 201
    detail = client.get(f"/api/tasks/{task_id}", headers=auth(assignee["access_token"]))
    assert len(detail.get_json()["data"]["comments"]) == 1

    forbidden_update = client.patch(
        f"/api/tasks/{task_id}",
        headers=auth(assignee["access_token"]),
        json={"status": "completed"},
    )
    assert forbidden_update.status_code == 403
    updated = client.patch(
        f"/api/tasks/{task_id}",
        headers=auth(owner["access_token"]),
        json={"status": "completed"},
    )
    assert updated.status_code == 200
    assert updated.get_json()["data"]["status"] == "completed"

    deleted = client.delete(f"/api/tasks/{task_id}", headers=auth(owner["access_token"]))
    assert deleted.status_code == 200
    not_found = client.get(f"/api/tasks/{task_id}", headers=auth(owner["access_token"]))
    assert not_found.status_code == 404
    assert not_found.get_json() == {"status": "error", "message": "Task not found"}


def test_task_validation_and_owner_isolation(client):
    first = create_account(client, "first@example.com", "First")
    second = create_account(client, "second@example.com", "Second")
    invalid = client.post("/api/tasks", headers=auth(first["access_token"]), json={"title": []})
    assert invalid.status_code == 400
    assert invalid.get_json()["errors"]["title"] == ["Title must be a string"]
    invalid_fields = client.post(
        "/api/tasks",
        headers=auth(first["access_token"]),
        json={"title": "", "priority": "urgent"},
    )
    assert invalid_fields.status_code == 400
    assert invalid_fields.get_json() == {
        "status": "error",
        "message": "Validation failed",
        "errors": {
            "title": ["Title is required", "Title must be at least 3 characters"],
            "priority": ["Priority must be one of: low, medium, high"],
        },
    }
    created = client.post(
        "/api/tasks",
        headers=auth(first["access_token"]),
        json={"title": "Private task"},
    )
    task_id = created.get_json()["data"]["id"]
    assert client.get(f"/api/tasks/{task_id}", headers=auth(second["access_token"])).status_code == 403
    assert client.get("/api/tasks?sort_by=invalid", headers=auth(first["access_token"])).status_code == 400