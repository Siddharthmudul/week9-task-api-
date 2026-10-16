"""Registration, login, token lifecycle, and password reset endpoints."""

from datetime import timedelta

from flask import Blueprint
from flask_jwt_extended import (
    create_access_token,
    decode_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from flask_jwt_extended.exceptions import JWTExtendedException
from sqlalchemy import func

from app.auth.utils import issue_tokens, send_password_reset_email
from app.extensions import db, limiter
from app.models import RevokedToken, User
from app.utils.responses import error, success
from app.utils.validators import json_object, validate_email, validate_username

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/register")
@limiter.limit("5 per minute")
def register():
    payload, problem = json_object()
    if problem:
        return error(problem, 400, "invalid_request")
    username = payload.get("username", payload.get("name"))
    email = payload.get("email")
    password = payload.get("password")
    problems = {}
    if not validate_username(username):
        problems["username"] = "Username must be 3-30 characters using letters, numbers, or underscores"
    if not validate_email(email):
        problems["email"] = "Must be a valid email address"
    if not isinstance(password, str) or len(password) < 8 or len(password) > 128:
        problems["password"] = "Must be between 8 and 128 characters"
    if problems:
        return error("Validation failed", 400, "validation_error", problems)
    normalized_email = email.strip().lower()
    if db.session.scalar(db.select(User).where(func.lower(User.email) == normalized_email)):
        return error("An account with this email already exists", 409, "email_exists")
    user = User(email=normalized_email, username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return success(
        {"message": "User registered successfully", "user": user.to_dict(), **issue_tokens(user)},
        201,
    )


@auth_bp.post("/login")
@limiter.limit("10 per minute")
def login():
    payload, problem = json_object()
    if problem:
        return error(problem, 400, "invalid_request")
    email, password = payload.get("email"), payload.get("password")
    if not isinstance(email, str) or not isinstance(password, str):
        return error("Validation failed", 400, "validation_error", {
            "email": ["Email is required"],
            "password": ["Password is required"],
        })
    user = db.session.scalar(db.select(User).where(func.lower(User.email) == email.strip().lower()))
    if user is None or not user.check_password(password):
        return error("Invalid email or password", 401, "invalid_credentials")
    return success({"user": user.to_dict(), **issue_tokens(user)})


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    user = db.session.get(User, int(identity))
    if user is None:
        return error("Account no longer exists", 401, "invalid_account")
    return success({"access_token": create_access_token(identity=str(user.id)), "token_type": "Bearer"})


@auth_bp.post("/logout")
@jwt_required()
def logout():
    db.session.add(RevokedToken(jti=get_jwt()["jti"]))
    db.session.commit()
    return success(message="Successfully logged out")


@auth_bp.post("/password-reset/request")
@limiter.limit("5 per hour")
def request_password_reset():
    payload, problem = json_object()
    if problem:
        return error(problem, 400, "invalid_request")
    email = payload.get("email")
    if not validate_email(email):
        return error("Validation failed", 400, "validation_error", {"email": ["A valid email address is required"]})
    user = db.session.scalar(db.select(User).where(func.lower(User.email) == email.strip().lower()))
    if user:
        token = create_access_token(
            identity=str(user.id),
            expires_delta=timedelta(minutes=30),
            additional_claims={"purpose": "password_reset"},
        )
        send_password_reset_email(user, token)
    return success(message="If the account exists, password reset instructions have been sent")


@auth_bp.post("/password-reset/confirm")
def confirm_password_reset():
    payload, problem = json_object()
    if problem:
        return error(problem, 400, "invalid_request")
    token, password = payload.get("token"), payload.get("password")
    if not isinstance(token, str) or not isinstance(password, str) or not 8 <= len(password) <= 128:
        return error(
            "Validation failed",
            400,
            "validation_error",
            {"token": ["A valid reset token is required"], "password": ["Password must be between 8 and 128 characters"]},
        )
    try:
        claims = decode_token(token)
    except JWTExtendedException:
        return error("Reset token is invalid or expired", 400, "invalid_reset_token")
    if claims.get("purpose") != "password_reset":
        return error("Reset token is invalid", 400, "invalid_reset_token")
    if db.session.get(RevokedToken, claims["jti"]) is not None:
        return error("Reset token has already been used", 400, "invalid_reset_token")
    user = db.session.get(User, int(claims["sub"]))
    if user is None:
        return error("Reset token is invalid", 400, "invalid_reset_token")
    user.set_password(password)
    db.session.add(RevokedToken(jti=claims["jti"]))
    db.session.commit()
    return success(message="Password has been reset")