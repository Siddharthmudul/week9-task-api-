"""Migrate task status values to the public API contract.

Revision ID: 7a2c91d4e6f0
Revises: bd46c93488d1
"""

from alembic import op

revision = "7a2c91d4e6f0"
down_revision = "bd46c93488d1"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE task SET status = 'pending' WHERE status = 'todo'")
    op.execute("UPDATE task SET status = 'completed' WHERE status = 'done'")


def downgrade():
    op.execute("UPDATE task SET status = 'todo' WHERE status = 'pending'")
    op.execute("UPDATE task SET status = 'done' WHERE status = 'completed'")
