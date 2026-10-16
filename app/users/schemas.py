"""User serialization helpers."""

from app.models import User


def serialize_user(user: User):
    return user.to_dict()