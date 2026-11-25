"""Motor y fábrica de sesiones de SQLAlchemy.

`pool_pre_ping` descarta conexiones muertas (PostgreSQL reiniciado, conexión
cortada por inactividad) antes de usarlas, en vez de fallar la primera request.
Crear el motor no abre conexiones: la app arranca aunque la base aún no esté,
y `/ready` lo refleja.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

# Tope de espera por una conexión del pool: mejor un 503 rápido que un cuelgue.
TIMEOUT_POOL_SEGUNDOS = 10
# Tope para abrir una conexión nueva. libpq no trae ninguno por defecto: con la
# base caída, /ready llegó a tardar 130 s en un test (2026-11-25) en vez de
# responder 503. El mínimo que acepta libpq es 2 s.
TIMEOUT_CONEXION_SEGUNDOS = 5


def crear_motor(url: str, timeout_conexion_s: int = TIMEOUT_CONEXION_SEGUNDOS) -> Engine:
    """Motor con pool verificado y timeouts; `connect_timeout` solo aplica a PostgreSQL."""
    argumentos: dict[str, Any] = {}
    if url.startswith("postgresql"):
        argumentos["connect_timeout"] = timeout_conexion_s
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_timeout=TIMEOUT_POOL_SEGUNDOS,
        connect_args=argumentos,
    )


def crear_sesiones(motor: Engine) -> sessionmaker[Session]:
    # expire_on_commit=False: los objetos siguen legibles tras cerrar la sesión,
    # que es justo cuando el repositorio los convierte a dominio.
    return sessionmaker(motor, expire_on_commit=False)
