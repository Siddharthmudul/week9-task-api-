"""Database models for accounts, tasks, comments, and revoked JWTs."""

from datetime import datetime, timezone

from sqlalchemy.orm import synonym
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


def format_utc_datetime(value):
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    username = db.Column("name", db.String(120), nullable=False)
    name = synonym("username")
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    created_tasks = db.relationship("Task", back_populates="owner", foreign_keys="Task.owner_id")
    assigned_tasks = db.relationship("Task", back_populates="assignee", foreign_keys="Task.assignee_id")
    comments = db.relationship("Comment", back_populates="author", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": format_utc_datetime(self.created_at),
        }


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False, default="")
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    priority = db.Column(db.String(20), nullable=False, default="medium", index=True)
    category = db.Column(db.String(80), nullable=True, index=True)
    due_date = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    assignee_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"), nullable=True, index=True)

    owner = db.relationship("User", back_populates="created_tasks", foreign_keys=[owner_id])
    assignee = db.relationship("User", back_populates="assigned_tasks", foreign_keys=[assignee_id])
    comments = db.relationship("Comment", back_populates="task", cascade="all, delete-orphan", order_by="Comment.created_at")

    def to_dict(self, include_comments=False):
        result = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "category": self.category,
            "due_date": self.due_date.date().isoformat() if self.due_date else None,
            "created_at": format_utc_datetime(self.created_at),
            "updated_at": format_utc_datetime(self.updated_at),
            "owner": self.owner.to_dict(),
            "assignee": self.assignee.to_dict() if self.assignee else None,
        }
        if include_comments:
            result["comments"] = [comment.to_dict() for comment in self.comments]
        return result


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(2000), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    task_id = db.Column(db.Integer, db.ForeignKey("task.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)

    task = db.relationship("Task", back_populates="comments")
    author = db.relationship("User", back_populates="comments")

    def to_dict(self):
        return {
            "id": self.id,
            "body": self.body,
            "created_at": format_utc_datetime(self.created_at),
            "author": self.author.to_dict(),
        }


class RevokedToken(db.Model):
    jti = db.Column(db.String(36), primary_key=True)
    revoked_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)