"""Allow shared movie matches to be hidden permanently.

Revision ID: 0003_movie_match_deleted
Revises: 0002_movie_matches
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_movie_match_deleted"
down_revision = "0002_movie_matches"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "movie_matches",
        sa.Column("deleted", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("movie_matches", "deleted")
