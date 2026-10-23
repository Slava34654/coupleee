"""Add public community map posts and reports.

Revision ID: 0004_community_map
Revises: 0003_movie_match_deleted
"""

from alembic import op


revision = "0004_community_map"
down_revision = "0003_movie_match_deleted"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE IF NOT EXISTS community_map_posts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pair_low_id INTEGER NOT NULL,
        pair_high_id INTEGER NOT NULL,
        created_by_user_id INTEGER NOT NULL,
        country_code TEXT NOT NULL,
        photo TEXT NOT NULL,
        comment TEXT NOT NULL,
        low_approved INTEGER NOT NULL DEFAULT 0,
        high_approved INTEGER NOT NULL DEFAULT 0,
        hidden INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(pair_low_id,pair_high_id,country_code))"""
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS community_map_posts_pair_idx "
        "ON community_map_posts(pair_low_id,pair_high_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS community_map_posts_visibility_idx "
        "ON community_map_posts(hidden,low_approved,high_approved,updated_at)"
    )
    op.execute(
        """CREATE TABLE IF NOT EXISTS community_map_reports(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        reporter_user_id INTEGER NOT NULL,
        reason TEXT NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE(post_id,reporter_user_id))"""
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS community_map_reports_post_idx "
        "ON community_map_reports(post_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS community_map_reports")
    op.execute("DROP TABLE IF EXISTS community_map_posts")
