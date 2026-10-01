import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

import app.models  # noqa: F401  (registers every table on Base.metadata)
from app.config import settings
from app.database import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Expression indexes (migration 0008): autogenerate cannot compare their expressions, so it would report them as
# changed on every check. They are created by the migration and declared on the model for create_all.
EXPRESSION_INDEXES = {"ix_students_state_key", "ix_students_state_district_key"}


def _include(obj, name, type_, reflected, compare_to):
    return not (type_ == "index" and name in EXPRESSION_INDEXES)


def _configure(**kwargs):
    context.configure(target_metadata=target_metadata, compare_type=True, compare_server_default=True,
                      include_object=_include,
                      # Each migration commits on its own: an enum value added by one migration (ALTER TYPE ... ADD
                      # VALUE) can only be used by a later one after that commit.
                      transaction_per_migration=True, **kwargs)


def run_migrations_offline() -> None:
    _configure(url=settings.DATABASE_URL, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def _run_sync(connection) -> None:
    _configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(settings.DATABASE_URL, poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(_run_sync)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
