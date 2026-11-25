"""Entorno de Alembic.

La URL sale de DATABASE_URL (la misma variable que usa la app), nunca de
alembic.ini, para no versionar credenciales. Los metadatos de las tablas se
toman de los modelos del adaptador SQLAlchemy (sirven a `--autogenerate`).
Si `config.attributes["connection"]` trae una conexión (tests), se usa esa y
no hace falta DATABASE_URL.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

import os

from alembic import context
from sqlalchemy import engine_from_config, pool

from applyops.adapters.outbound.modelos_sqlalchemy import Base

config = context.config
target_metadata = Base.metadata


def _url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("Falta DATABASE_URL para correr las migraciones")
    return url


def correr_offline() -> None:
    """Genera el SQL sin conectarse (alembic upgrade --sql)."""
    context.configure(url=_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def correr_online() -> None:
    """Aplica las migraciones contra la base de datos."""
    externa = config.attributes.get("connection")
    if externa is not None:
        context.configure(connection=externa, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
        return
    config.set_main_option("sqlalchemy.url", _url())
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
