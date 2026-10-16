"""Reusable request validation helpers."""

import re
from datetime import datetime, timezone

from flask import request

TASK_STATUSES = {"pending", "in_progress", "completed"}
TASK_PRIORITIES = {"low", "medium", "high"}
TASK_FIELDS = {"title", "description", "status", "priority", "category", "due_date", "assignee_id"}


def json_object():
    if not request.is_json:
        return None, "Content-Type must be application/json"
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return None, "Request body must be a JSON object"
    return payload, None


def validate_email(value):
    if not isinstance(value, str) or len(value) > 254:
        return False
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value.strip()))


def validate_username(value):
    return isinstance(value, str) and bool(re.fullmatch(r"[A-Za-z0-9_]{3,30}", value))


def parse_datetime(value):
    if not isinstance(value, str):
        raise ValueError("Must be an ISO 8601 datetime string")
    try:
        parsed_date = datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        parsed_date = None
    if parsed_date is not None:
        return parsed_date.replace(tzinfo=timezone.utc)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Datetime must include a timezone")
    return parsed


def validate_task_payload(payload, partial=False):
    errors = {}
    unknown = set(payload) - TASK_FIELDS
    if unknown:
        errors["unknown_fields"] = sorted(unknown)

    if not partial or "title" in payload:
        title = payload.get("title")
        if not isinstance(title, str):
            errors["title"] = ["Title is required"] if title is None else ["Title must be a string"]
        elif len(title.strip()) < 3:
            errors["title"] = ["Title is required", "Title must be at least 3 characters"] if not title.strip() else [
                "Title must be at least 3 characters"
            ]
        elif len(title.strip()) > 200:
            errors["title"] = ["Title must be no more than 200 characters"]

    if "description" in payload and (not isinstance(payload["description"], str) or len(payload["description"]) > 10000):
        errors["description"] = "Must be a string up to 10000 characters"
    if "status" in payload and (not isinstance(payload["status"], str) or payload["status"] not in TASK_STATUSES):
        errors["status"] = f"Must be one of: {', '.join(sorted(TASK_STATUSES))}"
    if "priority" in payload and (not isinstance(payload["priority"], str) or payload["priority"] not in TASK_PRIORITIES):
        errors["priority"] = "Priority must be one of: low, medium, high"
    if "category" in payload and payload["category"] is not None:
        if not isinstance(payload["category"], str) or len(payload["category"].strip()) > 80:
            errors["category"] = "Must be null or a string up to 80 characters"
    if "due_date" in payload and payload["due_date"] is not None:
        try:
            parse_datetime(payload["due_date"])
        except (TypeError, ValueError):
            errors["due_date"] = "Must be an ISO 8601 datetime with a timezone, or null"
    if "assignee_id" in payload and payload["assignee_id"] is not None:
        if not isinstance(payload["assignee_id"], int) or isinstance(payload["assignee_id"], bool) or payload["assignee_id"] < 1:
            errors["assignee_id"] = "Must be a positive integer or null"
    return errors