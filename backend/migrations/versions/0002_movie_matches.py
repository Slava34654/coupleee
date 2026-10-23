"""Add the shared movie match list for a couple.

Revision ID: 0002_movie_matches
Revises: 0001_current_schema
"""

from alembic import op


revision = "0002_movie_matches"
down_revision = "0001_current_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE IF NOT EXISTS movie_matches(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pair_low_id INTEGER NOT NULL,
        pair_high_id INTEGER NOT NULL,
        movie_id INTEGER NOT NULL,
        genre_key TEXT DEFAULT '',
        title TEXT DEFAULT '',
        title_en TEXT DEFAULT '',
        overview TEXT DEFAULT '',
        overview_en TEXT DEFAULT '',
        release_year INTEGER,
        poster_url TEXT DEFAULT '',
        genres TEXT DEFAULT '',
        runtime_min INTEGER,
        rating REAL,
        rating_source TEXT DEFAULT '',
        watched INTEGER NOT NULL DEFAULT 0,
        watched_at TEXT DEFAULT '',
        matched_at TEXT NOT NULL,
        UNIQUE(pair_low_id,pair_high_id,movie_id))"""
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS movie_matches_pair_idx "
        "ON movie_matches(pair_low_id,pair_high_id,watched,matched_at)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS movie_matches")
