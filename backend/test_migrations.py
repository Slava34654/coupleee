import sqlite3

from alembic.config import Config
from alembic.script import ScriptDirectory

from backend.database import upgrade_database


def columns(connection, table):
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def test_fresh_database_upgrades_to_head(tmp_path):
    db_path = tmp_path / "fresh.db"
    upgrade_database(str(db_path))

    connection = sqlite3.connect(db_path)
    revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    connection.close()

    config = Config("backend/alembic.ini")
    assert revision == ScriptDirectory.from_config(config).get_current_head()
    assert {
        "users",
        "auth_login_limits",
        "tg_payments",
        "referral_rewards",
        "referral_payouts",
        "photo_owners",
        "community_map_posts",
        "community_map_reports",
        "community_map_likes",
        "community_map_comments",
        "community_map_comment_reports",
    } <= tables


def test_existing_legacy_database_is_adopted_without_data_loss(tmp_path):
    db_path = tmp_path / "legacy.db"
    connection = sqlite3.connect(db_path)
    connection.executescript(
        """
        CREATE TABLE users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            pair_code TEXT UNIQUE NOT NULL,
            partner_id INTEGER,
            together_since TEXT NOT NULL);
        INSERT INTO users(name,pair_code,together_since)
            VALUES('Legacy user','LEGACY','2020-01-01');
        CREATE TABLE journal(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            text TEXT DEFAULT '',
            ts TEXT NOT NULL);
        """
    )
    connection.commit()
    connection.close()

    upgrade_database(str(db_path))

    connection = sqlite3.connect(db_path)
    user = connection.execute(
        "SELECT name,token,token_expires_at FROM users WHERE pair_code='LEGACY'"
    ).fetchone()
    assert user[0] == "Legacy user"
    assert user[1]
    assert user[2] > 0
    assert {"email", "password_hash", "token_expires_at", "premium_until"} <= columns(
        connection, "users"
    )
    assert {"fav", "photo"} <= columns(connection, "journal")
    assert connection.execute("SELECT version_num FROM alembic_version").fetchone()
    connection.close()
