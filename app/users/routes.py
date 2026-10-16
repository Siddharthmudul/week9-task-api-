"""Authenticated user profile endpoints."""

from flask import Blueprint
from flask_jwt_extended import jwt_required

from app.users.schemas import serialize_user
from app.utils.decorators import current_user_required
from app.utils.responses import success

users_bp = Blueprint("users", __name__)


@users_bp.get("/me")
@jwt_required()
@current_user_required
def get_current_user(user):
    return success(serialize_user(user))