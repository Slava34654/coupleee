"""Add bounded photo upload authorization and accounting.

Revision ID: 0011_secure_photo_uploads
Revises: 0010_clear_plaintext_user_tokens
"""

from alembic import op
import sqlalchemy as sa


revision = "0011_secure_photo_uploads"
down_revision = "0010_clear_plaintext_user_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("photo_owners") as batch_op:
        batch_op.add_column(
            sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0")
        )
    op.execute(
        """CREATE TABLE photo_upload_tokens(
        token_hash TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        expires_at_ms INTEGER NOT NULL,
        max_bytes INTEGER NOT NULL,
        consumed_at_ms INTEGER)"""
    )
    op.execute(
        """CREATE TABLE photo_upload_usage(
        user_id INTEGER PRIMARY KEY,
        day_utc TEXT NOT NULL,
        day_uploaded_bytes INTEGER NOT NULL DEFAULT 0)"""
    )
    op.execute(
        """CREATE TABLE photo_upload_limits(
        scope TEXT NOT NULL,
        key_hash TEXT NOT NULL,
        window_started_at_ms INTEGER NOT NULL,
        issued INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY(scope,key_hash))"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS photo_upload_limits")
    op.execute("DROP TABLE IF EXISTS photo_upload_usage")
    op.execute("DROP TABLE IF EXISTS photo_upload_tokens")
    with op.batch_alter_table("photo_owners") as batch_op:
        batch_op.drop_column("size_bytes")
