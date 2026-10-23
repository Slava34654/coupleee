"""Add referral reward choices and cash payout tracking.

Revision ID: 0007_referral_payouts
Revises: 0006_community_map_interactions
"""

from alembic import op


revision = "0007_referral_payouts"
down_revision = "0006_community_map_interactions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE referral_rewards(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        referred_tg_id INTEGER NOT NULL UNIQUE,
        referrer_user_id INTEGER NOT NULL,
        referred_user_id INTEGER NOT NULL,
        choice TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT 'awaiting_choice',
        amount_rub INTEGER NOT NULL DEFAULT 100,
        bonus_days INTEGER NOT NULL DEFAULT 7,
        payout_id INTEGER,
        created_at TEXT NOT NULL,
        chosen_at TEXT NOT NULL DEFAULT '')"""
    )
    op.execute(
        "CREATE INDEX referral_rewards_referrer_idx "
        "ON referral_rewards(referrer_user_id,status,id)"
    )
    op.execute(
        """CREATE TABLE referral_payouts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount_rub INTEGER NOT NULL,
        recipient TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT NOT NULL,
        paid_at TEXT NOT NULL DEFAULT '',
        admin_note TEXT NOT NULL DEFAULT '')"""
    )
    op.execute(
        "CREATE INDEX referral_payouts_status_idx "
        "ON referral_payouts(status,id)"
    )
    op.execute(
        "CREATE INDEX referral_payouts_user_idx "
        "ON referral_payouts(user_id,id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS referral_payouts")
    op.execute("DROP TABLE IF EXISTS referral_rewards")
