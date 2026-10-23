from logging.config import fileConfig
import os

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import URL


config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

if config.get_main_option("sqlalchemy.url") == "sqlite://":
    default_db = os.path.join(os.path.dirname(os.path.dirname(__file__)), "couple.db")
    db_path = os.environ.get("COUPLE_DB", default_db)
    config.set_main_option(
        "sqlalchemy.url",
        URL.create("sqlite", database=os.path.abspath(db_path)).render_as_string(
            hide_password=False
        ),
    )

target_metadata = None


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
