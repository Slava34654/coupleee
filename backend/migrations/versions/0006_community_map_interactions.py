"""Add likes and comments to community map posts.

Revision ID: 0006_community_map_interactions
Revises: 0005_community_map_points
"""

from alembic import op


revision = "0006_community_map_interactions"
down_revision = "0005_community_map_points"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE community_map_likes(
        post_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY(post_id,user_id))"""
    )
    op.execute(
        "CREATE INDEX community_map_likes_user_idx ON community_map_likes(user_id)"
    )
    op.execute(
        """CREATE TABLE community_map_comments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        author_user_id INTEGER NOT NULL,
        text TEXT NOT NULL,
        hidden INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL)"""
    )
    op.execute(
        "CREATE INDEX community_map_comments_post_idx "
        "ON community_map_comments(post_id,hidden,id)"
    )
    op.execute(
        "CREATE INDEX community_map_comments_author_idx "
        "ON community_map_comments(author_user_id)"
    )
    op.execute(
        """CREATE TABLE community_map_comment_reports(
        comment_id INTEGER NOT NULL,
        reporter_user_id INTEGER NOT NULL,
        reason TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY(comment_id,reporter_user_id))"""
    )
    op.execute(
        "CREATE INDEX community_map_comment_reports_reporter_idx "
        "ON community_map_comment_reports(reporter_user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS community_map_posts_visibility_idx "
        "ON community_map_posts(hidden,low_approved,high_approved,updated_at)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS community_map_comment_reports")
    op.execute("DROP TABLE IF EXISTS community_map_comments")
    op.execute("DROP TABLE IF EXISTS community_map_likes")
