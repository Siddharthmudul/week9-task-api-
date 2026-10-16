"""Task CRUD, filtering, assignment, and comments."""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from sqlalchemy import or_

from app.extensions import db
from app.models import Comment, Task, User
from app.tasks.schemas import serialize_task, serialize_task_list_item
from app.utils.decorators import accessible_task_required, current_user_required
from app.utils.responses import error, success
from app.utils.validators import (
    TASK_PRIORITIES,
    TASK_STATUSES,
    json_object,
    parse_datetime,
    validate_task_payload,
)

tasks_bp = Blueprint("tasks", __name__)


def apply_task_payload(task, payload):
    for field in ("title", "description", "status", "priority", "category"):
        if field in payload:
            value = payload[field]
            setattr(task, field, value.strip() if field in {"title", "category"} and isinstance(value, str) else value)
    if "due_date" in payload:
        task.due_date = parse_datetime(payload["due_date"]) if payload["due_date"] is not None else None
    if "assignee_id" in payload:
        task.assignee_id = payload["assignee_id"]


@tasks_bp.get("")
@jwt_required()
@current_user_required
def list_tasks(user):
    query = Task.query.filter(or_(Task.owner_id == user.id, Task.assignee_id == user.id))
    status = request.args.get("status")
    priority = request.args.get("priority")
    category = request.args.get("category")
    search = request.args.get("search", "").strip()
    requested_sort = request.args.get("sort_by")
    sort = requested_sort or request.args.get("sort", "created_at")
    order = request.args.get("sort_order", request.args.get("order", "desc"))
    if status:
        if status not in TASK_STATUSES:
            return error("Validation failed", 400, "validation_error", {
                "status": [f"Status must be one of: {', '.join(sorted(TASK_STATUSES))}"]
            })
        query = query.filter(Task.status == status)
    if priority:
        if priority not in TASK_PRIORITIES:
            return error("Validation failed", 400, "validation_error", {
                "priority": [f"Priority must be one of: {', '.join(sorted(TASK_PRIORITIES))}"]
            })
        query = query.filter(Task.priority == priority)
    if category:
        query = query.filter(Task.category == category)
    if search:
        pattern = f"%{search}%"
        query = query.filter(or_(Task.title.ilike(pattern), Task.description.ilike(pattern), Task.category.ilike(pattern)))
    allowed_sort_fields = {"created_at", "due_date", "priority"}
    if requested_sort is None:
        allowed_sort_fields.update({"updated_at", "title", "status"})
    if sort not in allowed_sort_fields:
        return error("Validation failed", 400, "validation_error", {
            "sort_by": ["Must be one of: created_at, due_date, priority"]
        })
    if order not in {"asc", "desc"}:
        return error("Validation failed", 400, "validation_error", {"sort_order": ["Must be 'asc' or 'desc'"]})
    column = getattr(Task, sort)
    query = query.order_by(column.asc() if order == "asc" else column.desc())
    try:
        page = max(1, int(request.args.get("page", "1")))
        per_page = min(100, max(1, int(request.args.get("per_page", "10"))))
    except ValueError:
        return error("Validation failed", 400, "validation_error", {
            "page": ["Page and per_page must be integers"],
            "per_page": ["Page and per_page must be integers"],
        })
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return success(
        {
            "tasks": [serialize_task_list_item(task) for task in pagination.items],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_pages": pagination.pages,
                "total_items": pagination.total,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev,
            },
        },
    )


@tasks_bp.post("")
@jwt_required()
@current_user_required
def create_task(user):
    payload, problem = json_object()
    if problem:
        return error(problem, 400, "invalid_request")
    errors = validate_task_payload(payload)
    if errors:
        return error("Validation failed", 400, "validation_error", errors)
    if payload.get("assignee_id") is not None and db.session.get(User, payload["assignee_id"]) is None:
        return error("Assignee not found", 404, "not_found")
    task = Task(owner=user)
    apply_task_payload(task, payload)
    db.session.add(task)
    db.session.commit()
    return success(serialize_task(task), 201)


@tasks_bp.get("/<int:task_id>")
@jwt_required()
@accessible_task_required()
def get_task(task):
    return success(serialize_task(task, include_comments=True))


@tasks_bp.put("/<int:task_id>")
@tasks_bp.patch("/<int:task_id>")
@jwt_required()
@accessible_task_required(owner_only=True)
def update_task(task):
    payload, problem = json_object()
    if problem:
        return error(problem, 400, "invalid_request")
    errors = validate_task_payload(payload, partial=request.method == "PATCH")
    if errors:
        return error("Validation failed", 400, "validation_error", errors)
    if request.method == "PUT" and "title" not in payload:
        return error("Validation failed", 400, "validation_error", {
            "title": ["PUT requires a complete task representation, including title"]
        })
    if request.method == "PUT":
        task.description = ""
        task.status = "pending"
        task.priority = "medium"
        task.category = None
        task.due_date = None
        task.assignee = None
    if payload.get("assignee_id") is not None:
        assignee = db.session.get(User, payload["assignee_id"])
        if assignee is None:
            return error("Assignee not found", 404, "not_found")
    apply_task_payload(task, payload)
    db.session.commit()
    return success(serialize_task(task))


@tasks_bp.delete("/<int:task_id>")
@jwt_required()
@accessible_task_required(owner_only=True)
def delete_task(task):
    db.session.delete(task)
    db.session.commit()
    return success(message="Task deleted")


@tasks_bp.post("/<int:task_id>/comments")
@jwt_required()
@current_user_required
@accessible_task_required()
def add_comment(user, task):
    payload, problem = json_object()
    if problem:
        return error(problem, 400, "invalid_request")
    body = payload.get("body")
    if not isinstance(body, str) or not body.strip() or len(body.strip()) > 2000:
        return error("Validation failed", 400, "validation_error", {
            "body": ["Comment body must be a non-empty string up to 2000 characters"]
        })
    comment = Comment(body=body.strip(), task=task, author=user)
    db.session.add(comment)
    db.session.commit()
    return success(comment.to_dict(), 201)


@tasks_bp.delete("/<int:task_id>/comments/<int:comment_id>")
@jwt_required()
@current_user_required
@accessible_task_required()
def delete_comment(user, task, comment_id):
    comment = db.session.get(Comment, comment_id)
    if comment is None or comment.task_id != task.id:
        return error("Comment not found", 404, "not_found")
    if comment.author_id != user.id and task.owner_id != user.id:
        return error("Only the comment author or task owner can delete this comment", 403, "forbidden")
    db.session.delete(comment)
    db.session.commit()
    return success(message="Comment deleted")