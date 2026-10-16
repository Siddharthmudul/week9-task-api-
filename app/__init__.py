"""Flask application factory and shared HTTP error handling."""

import logging
from logging.config import dictConfig
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, send_from_directory
from flask_jwt_extended.exceptions import JWTExtendedException
from flask_limiter.errors import RateLimitExceeded
from sqlalchemy.exc import SQLAlchemyError

from config import Config
from app.extensions import cors, db, jwt, limiter, mail, migrate
from app.utils.responses import error as error_response


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    dictConfig(
        {
            "version": 1,
            "formatters": {"default": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}},
            "handlers": {"wsgi": {"class": "logging.StreamHandler", "formatter": "default"}},
            "root": {"level": "INFO", "handlers": ["wsgi"]},
        }
    )

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    mail.init_app(app)
    cors.init_app(app, origins=app.config["CORS_ORIGINS"])
    limiter.init_app(app)

    from app import models  # noqa: F401
    from app.auth.routes import auth_bp
    from app.tasks.routes import tasks_bp
    from app.users.routes import users_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(tasks_bp, url_prefix="/api/tasks")
    app.register_blueprint(users_bp, url_prefix="/api/users")
    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth", name="auth_v1")
    app.register_blueprint(tasks_bp, url_prefix="/api/v1/tasks", name="tasks_v1")
    app.register_blueprint(users_bp, url_prefix="/api/v1/users", name="users_v1")

    @app.get("/")
    def index():
        return redirect("/docs")

    @app.get("/docs")
    @app.get("/docs/")
    def api_docs():
        return render_template("docs.html")

    @app.get("/docs/files/<path:filename>")
    def documentation_file(filename):
        return send_from_directory(Path(app.root_path).parent / "docs", filename)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.errorhandler(404)
    def not_found(_error):
        return error_response("Resource not found", 404)

    @app.errorhandler(405)
    def method_not_allowed(_error):
        return error_response("Method not allowed", 405)

    @app.errorhandler(RateLimitExceeded)
    def rate_limit_exceeded(exception):
        return error_response(str(exception), 429)

    @app.errorhandler(SQLAlchemyError)
    def database_error(exception):
        db.session.rollback()
        app.logger.exception("Database operation failed", exc_info=exception)
        return error_response("A database error occurred", 500)

    @app.errorhandler(Exception)
    def unexpected_error(exception):
        app.logger.exception("Unhandled request error", exc_info=exception)
        return error_response("An unexpected error occurred", 500)

    @jwt.unauthorized_loader
    def missing_token(reason):
        return error_response("Missing or invalid token", 401)

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return error_response("Missing or invalid token", 401)

    @jwt.expired_token_loader
    def expired_token(_header, _payload):
        return error_response("Token has expired", 401)

    @jwt.revoked_token_loader
    def revoked_token(_header, _payload):
        return error_response("Token has been revoked", 401)

    @jwt.token_in_blocklist_loader
    def token_is_revoked(_header, payload):
        from app.models import RevokedToken

        return db.session.get(RevokedToken, payload["jti"]) is not None

    @jwt.token_verification_loader
    def reject_password_reset_access_tokens(_header, payload):
        return payload.get("purpose") != "password_reset"

    @jwt.token_verification_failed_loader
    def token_verification_failed(_header, _payload):
        return error_response("This token cannot be used for this operation", 401)

    return app