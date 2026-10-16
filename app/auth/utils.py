"""Reusable authentication and email helpers."""

from flask import current_app
from flask_mail import Message
from flask_jwt_extended import create_access_token, create_refresh_token

from app.extensions import mail


def issue_tokens(user):
    identity = str(user.id)
    return {
        "access_token": create_access_token(identity=identity),
        "refresh_token": create_refresh_token(identity=identity),
        "token_type": "Bearer",
    }


def send_password_reset_email(user, token):
    sender = current_app.config.get("MAIL_DEFAULT_SENDER")
    if not sender or not current_app.config.get("MAIL_SERVER"):
        current_app.logger.error("Password reset email not sent: mail settings are incomplete")
        return False
    url = f"{current_app.config['PASSWORD_RESET_URL']}?token={token}"
    message = Message(
        subject="Reset your task API password",
        recipients=[user.email],
        body=f"Use this link to reset your password. It expires in 30 minutes:\n\n{url}",
    )
    mail.send(message)
    return True