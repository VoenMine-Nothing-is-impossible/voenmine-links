import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import settings  # noqa: E402
from app.database import Base  # noqa: E402
from app import models  # noqa: E402,F401

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url():
    return os.getenv("DATABASE_URL", settings.DATABASE_URL)


def run_migrations_offline():
    context.configure(url=get_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    cfg = config.get_section(config.config_ini_section) or {}
    cfg["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(cfg, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
