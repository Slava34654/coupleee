"""Store session token digests.

Revision ID: 0009_user_token_hash
Revises: 0008_private_photos
"""

import hashlib

from alembic import op
import sqlalchemy as sa


revision = "0009_user_token_hash"
down_revision = "0008_private_photos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("token_hash", sa.Text(), nullable=True))

    bind = op.get_bind()
    users = bind.execute(
        sa.text("SELECT id,token FROM users WHERE token IS NOT NULL AND token!=''")
    ).fetchall()
    for user in users:
        digest = hashlib.sha256(user.token.encode("utf-8")).hexdigest()
        bind.execute(
            sa.text("UPDATE users SET token_hash=:digest WHERE id=:id"),
            {"digest": digest, "id": user.id},
        )

    op.create_index(
        "users_token_hash_uq",
        "users",
        ["token_hash"],
        unique=True,
        sqlite_where=sa.text("token_hash IS NOT NULL AND token_hash != ''"),
    )


def downgrade() -> None:
    op.drop_index("users_token_hash_uq", table_name="users")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("token_hash")
