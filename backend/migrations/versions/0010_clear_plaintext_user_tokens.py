"""Remove plaintext session tokens.

Revision ID: 0010_clear_plaintext_user_tokens
Revises: 0009_user_token_hash
"""

from alembic import op


revision = "0010_clear_plaintext_user_tokens"
down_revision = "0009_user_token_hash"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE users SET token='' WHERE token IS NOT NULL AND token!=''")


def downgrade() -> None:
    raise RuntimeError("Plaintext session tokens cannot be recovered from their hashes")
