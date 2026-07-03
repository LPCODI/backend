"""Alembic environment configuration."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.db.migrations import get_migration_database_url, get_migration_metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = get_migration_metadata()


def _set_database_url() -> str:
    database_url = get_migration_database_url()
    config.set_main_option("sqlalchemy.url", database_url)
    return database_url


def run_migrations_offline() -> None:
    """Run migrations without opening a DB connection."""

    context.configure(
        url=_set_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations with a live DB connection."""

    _set_database_url()
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
