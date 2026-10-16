"""Task serialization helpers."""

from app.models import Task


def serialize_task(task: Task, include_comments=False):
    return task.to_dict(include_comments=include_comments)


def serialize_task_list_item(task: Task):
    serialized = task.to_dict()
    return {
        "id": serialized["id"],
        "title": serialized["title"],
        "description": serialized["description"],
        "status": serialized["status"],
        "priority": serialized["priority"],
        "due_date": serialized["due_date"],
        "created_at": serialized["created_at"],
        "updated_at": serialized["updated_at"],
    }