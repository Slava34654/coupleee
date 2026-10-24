import hashlib
import sqlite3

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from backend.database import upgrade_database


def columns(connection, table):
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def migration_config(db_path):
    config = Config("backend/alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path.as_posix()}")
    return config


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
        "photo_upload_tokens",
        "photo_upload_usage",
        "photo_upload_limits",
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
        "SELECT name,token,token_hash,token_expires_at "
        "FROM users WHERE pair_code='LEGACY'"
    ).fetchone()
    assert user[0] == "Legacy user"
    assert user[1] == ""
    assert len(user[2]) == 64
    assert user[3] > 0
    assert {
        "email",
        "password_hash",
        "token_hash",
        "token_expires_at",
        "premium_until",
    } <= columns(connection, "users")
    assert {"fav", "photo"} <= columns(connection, "journal")
    assert connection.execute("SELECT version_num FROM alembic_version").fetchone()
    connection.close()


def test_token_hash_migration_is_reversible(tmp_path):
    db_path = tmp_path / "token-hash.db"
    config = migration_config(db_path)
    command.upgrade(config, "0008_private_photos")

    raw_token = "legacy-raw-token"
    connection = sqlite3.connect(db_path)
    connection.execute(
        "INSERT INTO users(name,pair_code,together_since,token,token_expires_at) "
        "VALUES('Legacy','TOKEN1','2020-01-01',?,9999999999999)",
        (raw_token,),
    )
    connection.commit()
    connection.close()

    command.upgrade(config, "0009_user_token_hash")
    connection = sqlite3.connect(db_path)
    token, token_hash = connection.execute(
        "SELECT token,token_hash FROM users WHERE pair_code='TOKEN1'"
    ).fetchone()
    connection.close()
    assert token == raw_token
    assert token_hash == hashlib.sha256(raw_token.encode()).hexdigest()

    command.downgrade(config, "0008_private_photos")
    connection = sqlite3.connect(db_path)
    assert "token_hash" not in columns(connection, "users")
    assert connection.execute(
        "SELECT token FROM users WHERE pair_code='TOKEN1'"
    ).fetchone()[0] == raw_token
    connection.close()
