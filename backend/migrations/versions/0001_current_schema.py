"""Create or adopt the current Enrwine schema.

Revision ID: 0001_current_schema
Revises: None
"""
import secrets
import time

from alembic import op
import sqlalchemy as sa


revision = "0001_current_schema"
down_revision = None
branch_labels = None
depends_on = None

TOKEN_TTL_MS = 30 * 24 * 60 * 60 * 1000

SCHEMA_STATEMENTS = (
    """CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        pair_code TEXT UNIQUE NOT NULL,
        partner_id INTEGER,
        together_since TEXT NOT NULL,
        birth TEXT DEFAULT '', avatar TEXT DEFAULT '', token TEXT DEFAULT '',
        email TEXT, password_hash TEXT, token_expires_at INTEGER DEFAULT 0,
        pair_ready INTEGER NOT NULL DEFAULT 1, premium_until TEXT DEFAULT '')""",
    """CREATE TABLE IF NOT EXISTS moods(
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
        mood TEXT NOT NULL, note TEXT DEFAULT '', ts TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS answers(
        user_id INTEGER NOT NULL, qdate TEXT NOT NULL, qindex INTEGER NOT NULL,
        text TEXT NOT NULL, ts TEXT NOT NULL,
        PRIMARY KEY(user_id,qdate,qindex))""",
    """CREATE TABLE IF NOT EXISTS quiz_categories(
        id INTEGER PRIMARY KEY AUTOINCREMENT, seed_key TEXT NOT NULL UNIQUE,
        title TEXT NOT NULL, position INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS quizzes(
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
        category_id INTEGER, seed_key TEXT, position INTEGER)""",
    """CREATE TABLE IF NOT EXISTS quiz_q(
        id INTEGER PRIMARY KEY AUTOINCREMENT, quiz_id INTEGER NOT NULL,
        text TEXT NOT NULL, options TEXT NOT NULL, seed_key TEXT, position INTEGER)""",
    """CREATE TABLE IF NOT EXISTS quiz_a(
        user_id INTEGER NOT NULL, quiz_id INTEGER NOT NULL,
        qid INTEGER NOT NULL, option INTEGER NOT NULL,
        PRIMARY KEY(user_id,quiz_id,qid))""",
    """CREATE TABLE IF NOT EXISTS ideas(
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
        category TEXT DEFAULT '', budget TEXT DEFAULT '', done INTEGER DEFAULT 0)""",
    """CREATE TABLE IF NOT EXISTS journal(
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
        title TEXT NOT NULL, text TEXT DEFAULT '', ts TEXT NOT NULL,
        fav INTEGER DEFAULT 0, photo TEXT DEFAULT '')""",
    """CREATE TABLE IF NOT EXISTS events(
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
        title TEXT NOT NULL, date TEXT NOT NULL, icon TEXT DEFAULT '',
        repeat INTEGER DEFAULT 0)""",
    """CREATE TABLE IF NOT EXISTS wishlist(
        id INTEGER PRIMARY KEY AUTOINCREMENT, pair_key TEXT NOT NULL,
        author_id INTEGER NOT NULL, title TEXT NOT NULL, photo TEXT DEFAULT '',
        done INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
        completed_at TEXT DEFAULT '')""",
    """CREATE TABLE IF NOT EXISTS packs(
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
        description TEXT DEFAULT '', kind TEXT DEFAULT 'short')""",
    """CREATE TABLE IF NOT EXISTS pack_q(
        id INTEGER PRIMARY KEY AUTOINCREMENT, pack_id INTEGER NOT NULL,
        text TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS pack_a(
        user_id INTEGER NOT NULL, pack_id INTEGER NOT NULL,
        qid INTEGER NOT NULL, text TEXT NOT NULL, ts TEXT NOT NULL,
        photo TEXT DEFAULT '', PRIMARY KEY(user_id,pack_id,qid))""",
    """CREATE TABLE IF NOT EXISTS taps(
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
        ts TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS journal_likes(
        entry_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        PRIMARY KEY(entry_id,user_id))""",
    """CREATE TABLE IF NOT EXISTS widget_photos(
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
        photo TEXT NOT NULL, caption TEXT DEFAULT '', ts TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS couple_games(
        pair_key TEXT NOT NULL, kind TEXT NOT NULL, state TEXT NOT NULL,
        version INTEGER NOT NULL DEFAULT 1, updated_at TEXT NOT NULL,
        PRIMARY KEY(pair_key,kind))""",
    """CREATE TABLE IF NOT EXISTS companions(
        pair_key TEXT PRIMARY KEY, state TEXT NOT NULL,
        proposal_type TEXT DEFAULT '', proposal_name TEXT DEFAULT '',
        proposed_by INTEGER, version INTEGER NOT NULL DEFAULT 1,
        updated_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS push_tokens(
        token TEXT PRIMARY KEY, user_id INTEGER NOT NULL,
        platform TEXT NOT NULL DEFAULT 'android', updated_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS movie_rounds(
        id INTEGER PRIMARY KEY AUTOINCREMENT, pair_low_id INTEGER NOT NULL,
        pair_high_id INTEGER NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('active','matched','exhausted')),
        matched_movie_id INTEGER, genre_key TEXT,
        catalog_source TEXT NOT NULL DEFAULT 'tmdb', created_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS movie_swipes(
        round_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        movie_id INTEGER NOT NULL,
        decision TEXT NOT NULL CHECK(decision IN ('heart','skip')),
        created_at TEXT NOT NULL, PRIMARY KEY(round_id,user_id,movie_id))""",
    """CREATE TABLE IF NOT EXISTS auth_login_limits(
        scope TEXT NOT NULL, key_hash TEXT NOT NULL,
        failures INTEGER NOT NULL DEFAULT 0, window_started_at INTEGER NOT NULL,
        blocked_until INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(scope,key_hash))""",
    """CREATE TABLE IF NOT EXISTS locations(
        user_id INTEGER PRIMARY KEY, lat REAL NOT NULL, lon REAL NOT NULL,
        ts TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS exact_widget_shares(
        owner_id INTEGER PRIMARY KEY, grantee_id INTEGER NOT NULL,
        lat REAL, lon REAL, location_ts TEXT, consented_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS tg(
        user_id INTEGER PRIMARY KEY, tg_id INTEGER UNIQUE,
        tg_name TEXT DEFAULT '', ts TEXT DEFAULT '')""",
    """CREATE TABLE IF NOT EXISTS refs(
        tg_id INTEGER PRIMARY KEY, referrer INTEGER NOT NULL,
        ts TEXT DEFAULT '', rewarded INTEGER DEFAULT 0)""",
    """CREATE TABLE IF NOT EXISTS tg_payments(
        charge_id TEXT PRIMARY KEY, provider_charge_id TEXT DEFAULT '',
        user_id INTEGER, tg_id INTEGER, currency TEXT NOT NULL,
        total_amount INTEGER NOT NULL, payload TEXT NOT NULL, ts TEXT NOT NULL)""",
)


LEGACY_COLUMNS = {
    "journal": (
        sa.Column("fav", sa.Integer(), server_default="0"),
        sa.Column("photo", sa.Text(), server_default=""),
    ),
    "events": (
        sa.Column("icon", sa.Text(), server_default=""),
        sa.Column("repeat", sa.Integer(), server_default="0"),
    ),
    "wishlist": (sa.Column("photo", sa.Text(), server_default=""),),
    "users": (
        sa.Column("birth", sa.Text(), server_default=""),
        sa.Column("avatar", sa.Text(), server_default=""),
        sa.Column("token", sa.Text(), server_default=""),
        sa.Column("email", sa.Text()),
        sa.Column("password_hash", sa.Text()),
        sa.Column("token_expires_at", sa.Integer(), server_default="0"),
        sa.Column("pair_ready", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("premium_until", sa.Text(), server_default=""),
    ),
    "quizzes": (
        sa.Column("category_id", sa.Integer()),
        sa.Column("seed_key", sa.Text()),
        sa.Column("position", sa.Integer()),
    ),
    "quiz_q": (
        sa.Column("seed_key", sa.Text()),
        sa.Column("position", sa.Integer()),
    ),
    "packs": (sa.Column("kind", sa.Text(), server_default="short"),),
    "pack_a": (sa.Column("photo", sa.Text(), server_default=""),),
}


def _add_legacy_columns() -> None:
    bind = op.get_bind()
    for table_name, columns in LEGACY_COLUMNS.items():
        existing = {column["name"] for column in sa.inspect(bind).get_columns(table_name)}
        for column in columns:
            if column.name not in existing:
                op.add_column(table_name, column)

    movie_columns = {
        column["name"] for column in sa.inspect(bind).get_columns("movie_rounds")
    }
    if "genre_key" not in movie_columns:
        op.add_column("movie_rounds", sa.Column("genre_key", sa.Text()))
        op.execute(
            "UPDATE movie_rounds SET genre_key=CASE "
            "WHEN status='active' AND NOT EXISTS ("
            "SELECT 1 FROM movie_swipes WHERE movie_swipes.round_id=movie_rounds.id"
            ") THEN NULL ELSE 'all' END WHERE genre_key IS NULL"
        )
    if "catalog_source" not in movie_columns:
        op.add_column("movie_rounds", sa.Column("catalog_source", sa.Text()))
        op.execute("DELETE FROM movie_swipes")
        op.execute("DELETE FROM movie_rounds")


def upgrade() -> None:
    for statement in SCHEMA_STATEMENTS:
        op.execute(statement)
    _add_legacy_columns()

    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS users_email_uq "
        "ON users(email) WHERE email IS NOT NULL AND email != ''"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS wishlist_pair_idx "
        "ON wishlist(pair_key,done,created_at)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS quizzes_seed_idx ON quizzes(seed_key)")
    op.execute("CREATE INDEX IF NOT EXISTS quiz_q_seed_idx ON quiz_q(seed_key)")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS movie_rounds_one_active "
        "ON movie_rounds(pair_low_id,pair_high_id) WHERE status='active'"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS movie_swipes_round_user "
        "ON movie_swipes(round_id,user_id)"
    )
    op.execute("DROP TABLE IF EXISTS movies")

    bind = op.get_bind()
    expires_at = int(time.time() * 1000) + TOKEN_TTL_MS
    rows = bind.execute(
        sa.text("SELECT id FROM users WHERE token IS NULL OR token='' ")
    ).fetchall()
    for row in rows:
        bind.execute(
            sa.text("UPDATE users SET token=:token,token_expires_at=:expires WHERE id=:id"),
            {"token": secrets.token_hex(16), "expires": expires_at, "id": row.id},
        )
    bind.execute(
        sa.text(
            "UPDATE users SET token_expires_at=:expires "
            "WHERE token IS NOT NULL AND token!='' AND COALESCE(token_expires_at,0)<=0"
        ),
        {"expires": expires_at},
    )


def downgrade() -> None:
    raise RuntimeError("The initial production schema migration is irreversible")
