"""Entorno de Alembic.

La URL sale de DATABASE_URL (la misma variable que usa la app), nunca de
alembic.ini, para no versionar credenciales. Los metadatos de las tablas se
toman de los modelos del adaptador SQLAlchemy cuando existan.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

import os

from alembic import context
from sqlalchemy import MetaData, engine_from_config, pool

config = context.config
url = os.environ.get("DATABASE_URL")
if not url:
    raise RuntimeError("Falta DATABASE_URL para correr las migraciones")
config.set_main_option("sqlalchemy.url", url)

target_metadata: MetaData | None = None


def correr_offline() -> None:
    """Genera el SQL sin conectarse (alembic upgrade --sql)."""
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def correr_online() -> None:
    """Aplica las migraciones contra la base de datos."""
    motor = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with motor.connect() as conexion:
        context.configure(connection=conexion, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    correr_offline()
else:
    correr_online()
