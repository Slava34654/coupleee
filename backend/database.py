import os

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import URL


def sqlite_url(db_path: str) -> str:
    return URL.create("sqlite", database=os.path.abspath(db_path)).render_as_string(
        hide_password=False
    )


def upgrade_database(db_path: str) -> None:
    config_path = os.path.join(os.path.dirname(__file__), "alembic.ini")
    config = Config(config_path)
    config.set_main_option("sqlalchemy.url", sqlite_url(db_path))
    command.upgrade(config, "head")
