"""Track photo ownership for authenticated media access.

Revision ID: 0008_private_photos
Revises: 0007_referral_payouts
"""

from alembic import op


revision = "0008_private_photos"
down_revision = "0007_referral_payouts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE photo_owners(
        name TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY(name,user_id))"""
    )
    op.execute("CREATE INDEX photo_owners_user_idx ON photo_owners(user_id,name)")

    # Preserve access to media uploaded before ownership tracking existed.
    for table, user_column, photo_column in (
        ("users", "id", "avatar"),
        ("journal", "user_id", "photo"),
        ("wishlist", "author_id", "photo"),
        ("pack_a", "user_id", "photo"),
        ("widget_photos", "user_id", "photo"),
        ("community_map_posts", "created_by_user_id", "photo"),
    ):
        op.execute(
            f"INSERT OR IGNORE INTO photo_owners(name,user_id,created_at) "
            f"SELECT substr({photo_column},instr({photo_column},'/photos/')+8),"
            f"{user_column},datetime('now') FROM {table} "
            f"WHERE instr({photo_column},'/photos/')>0"
        )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS photo_owners")
