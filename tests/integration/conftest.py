"""Base de datos real para los tests de integración, creada con las migraciones.

Usa `DATABASE_URL_TEST` (PostgreSQL en CI) o, si no está, SQLite en memoria.
El esquema se crea con `alembic upgrade head` (no con `create_all`), así cada
corrida prueba también las migraciones, y se baja con `downgrade base` al final
para dejar limpia una base compartida.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

RAIZ = Path(__file__).resolve().parents[2]


def _config_alembic(motor: Engine) -> Config:
    config = Config(str(RAIZ / "alembic.ini"))
    config.set_main_option("script_location", str(RAIZ / "migrations"))
    return config


def _migrar(motor: Engine, destino: str, subir: bool) -> None:
    config = _config_alembic(motor)
    with motor.begin() as conexion:
        config.attributes["connection"] = conexion
        if subir:
            command.upgrade(config, destino)
        else:
            command.downgrade(config, destino)


@pytest.fixture
def motor() -> Iterator[Engine]:
    url = os.environ.get("DATABASE_URL_TEST")
    if url:
        motor = create_engine(url)
    else:
        # StaticPool: una sola conexión, si no cada sesión vería otra base en memoria vacía.
        motor = create_engine(
            "sqlite+pysqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
    _migrar(motor, "head", subir=True)
    try:
        yield motor
    finally:
        _migrar(motor, "base", subir=False)
        motor.dispose()


@pytest.fixture
def sesiones(motor: Engine) -> sessionmaker[Session]:
    return sessionmaker(motor, expire_on_commit=False)
