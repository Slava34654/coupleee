"""Add exact point coordinates to community map posts.

Revision ID: 0005_community_map_points
Revises: 0004_community_map
"""

from alembic import op


revision = "0005_community_map_points"
down_revision = "0004_community_map"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE community_map_posts_new(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pair_low_id INTEGER NOT NULL,
        pair_high_id INTEGER NOT NULL,
        created_by_user_id INTEGER NOT NULL,
        country_code TEXT,
        lat REAL NOT NULL DEFAULT 0,
        lon REAL NOT NULL DEFAULT 0,
        photo TEXT NOT NULL,
        comment TEXT NOT NULL,
        low_approved INTEGER NOT NULL DEFAULT 0,
        high_approved INTEGER NOT NULL DEFAULT 0,
        hidden INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL)"""
    )
    op.execute(
        "INSERT INTO community_map_posts_new("
        "id,pair_low_id,pair_high_id,created_by_user_id,country_code,"
        "lat,lon,photo,comment,low_approved,high_approved,hidden,created_at,updated_at) "
        "SELECT id,pair_low_id,pair_high_id,created_by_user_id,country_code,0,0,"
        "photo,comment,low_approved,high_approved,hidden,created_at,updated_at "
        "FROM community_map_posts"
    )
    op.execute("DROP TABLE community_map_posts")
    op.execute("ALTER TABLE community_map_posts_new RENAME TO community_map_posts")
    op.execute(
        "CREATE INDEX IF NOT EXISTS community_map_posts_pair_idx "
        "ON community_map_posts(pair_low_id,pair_high_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS community_map_posts_point_idx "
        "ON community_map_posts(lat,lon)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS community_map_posts_point_idx")
    op.execute(
        """CREATE TABLE community_map_posts_old(
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
        "INSERT INTO community_map_posts_old("
        "id,pair_low_id,pair_high_id,created_by_user_id,country_code,"
        "photo,comment,low_approved,high_approved,hidden,created_at,updated_at) "
        "SELECT id,pair_low_id,pair_high_id,created_by_user_id,COALESCE(country_code,''),"
        "photo,comment,low_approved,high_approved,hidden,created_at,updated_at "
        "FROM community_map_posts"
    )
    op.execute("DROP TABLE community_map_posts")
    op.execute("ALTER TABLE community_map_posts_old RENAME TO community_map_posts")
    op.execute(
        "CREATE INDEX IF NOT EXISTS community_map_posts_pair_idx "
        "ON community_map_posts(pair_low_id,pair_high_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS community_map_posts_visibility_idx "
        "ON community_map_posts(hidden,low_approved,high_approved,updated_at)"
    )
