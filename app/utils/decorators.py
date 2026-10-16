"""Request decorators shared across blueprints."""

from functools import wraps

from flask_jwt_extended import get_jwt_identity

from app.extensions import db
from app.models import Task, User
from app.utils.responses import error


def current_user_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        user = db.session.get(User, int(get_jwt_identity()))
        if user is None:
            return error("Account no longer exists", 401, "invalid_account")
        return function(user, *args, **kwargs)

    return wrapper


def accessible_task_required(owner_only=False):
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            user = args[0] if args and isinstance(args[0], User) else None
            if user is not None:
                task_id = args[1] if len(args) > 1 else kwargs.pop("task_id", None)
                remaining_args = args[2:]
            else:
                task_id = args[0] if args else kwargs.pop("task_id", None)
                remaining_args = args[1:]
            user_id = int(get_jwt_identity())
            task = db.session.get(Task, task_id)
            if task is None:
                return error("Task not found", 404, "not_found")
            if task.owner_id != user_id and (owner_only or task.assignee_id != user_id):
                return error("You do not have access to this task", 403, "forbidden")
            return function(user, task, *remaining_args, **kwargs) if user is not None else function(task, *remaining_args, **kwargs)

        return wrapper

    return decorator