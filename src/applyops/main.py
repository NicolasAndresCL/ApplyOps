"""Composition root de ApplyOps.

Es el único módulo que conoce las clases concretas: lee `Settings`, arma
fuentes, repositorio y casos de uso, y se los entrega a la app FastAPI en un
`Contenedor`. Los tests llaman a `crear_app(contenedor)` con fakes.

Se levanta con `uvicorn applyops.main:crear_app --factory`: importar este
módulo no lee el entorno ni abre conexiones.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI

from applyops import __version__
from applyops.adapters.inbound.api import ofertas, recolecciones, salud
from applyops.adapters.inbound.api.contenedor import Contenedor
from applyops.adapters.inbound.api.correlacion import middleware_correlacion
from applyops.adapters.inbound.api.errores import registrar_manejadores
from applyops.adapters.outbound.getonboard import FuenteGetOnBoard
from applyops.adapters.outbound.http_resiliente import ClienteHttpResiliente, crear_cliente
from applyops.adapters.outbound.perfil_yaml import cargar_perfil
from applyops.adapters.outbound.repo_sqlalchemy import RepoOfertasSqlAlchemy
from applyops.application.consultar import ConsultarOfertas
from applyops.application.recolectar import RecolectarOfertas
from applyops.application.registrar_manual import RegistrarOfertaManual
from applyops.infra.db import crear_motor, crear_sesiones
from applyops.infra.logs import configurar_logs
from applyops.infra.programador import recolectar_periodicamente
from applyops.infra.settings import Settings

logger = logging.getLogger(__name__)

SEGUNDOS_POR_HORA = 3600


def _ahora() -> datetime:
    return datetime.now(UTC)


def construir_contenedor(settings: Settings) -> tuple[Contenedor, Callable[[], None]]:
    """Arma el grafo de dependencias reales. Devuelve también cómo liberar sus recursos."""
    perfil = cargar_perfil(settings.perfil_busqueda_path)
    motor = crear_motor(settings.database_url)
    repo = RepoOfertasSqlAlchemy(crear_sesiones(motor), reloj=_ahora)
    cliente = crear_cliente(settings.http_timeout_segundos)
    fuentes = [
        FuenteGetOnBoard(
            ClienteHttpResiliente(cliente, "getonboard", intentos=settings.http_reintentos),
            url_base=settings.getonboard_url_base,
            max_paginas=settings.getonboard_max_paginas,
        ),
    ]
    contenedor = Contenedor(
        recolectar=RecolectarOfertas(fuentes, repo, perfil, reloj=_ahora),
        consultar=ConsultarOfertas(repo),
        registrar=RegistrarOfertaManual(repo, perfil, reloj=_ahora),
        repo=repo,
    )

    def liberar() -> None:
        cliente.close()
        motor.dispose()

    return contenedor, liberar


def crear_app(contenedor: Contenedor | None = None, intervalo_horas: float = 0) -> FastAPI:
    """Construye la app. Sin `contenedor`, lo arma desde el entorno (producción)."""
    liberar: Callable[[], None] = lambda: None  # noqa: E731 - no-op si el contenedor viene de afuera
    if contenedor is None:
        settings = Settings()
        configurar_logs(settings.log_level)
        contenedor, liberar = construir_contenedor(settings)
        intervalo_horas = settings.recoleccion_intervalo_horas
    recolectar = contenedor.recolectar

    @asynccontextmanager
    async def ciclo_de_vida(_: FastAPI) -> AsyncIterator[None]:
        tarea: asyncio.Task[None] | None = None
        if intervalo_horas > 0:
            tarea = asyncio.create_task(
                recolectar_periodicamente(recolectar, intervalo_horas * SEGUNDOS_POR_HORA)
            )
            logger.info("Recolección programada", extra={"cada_horas": intervalo_horas})
        try:
            yield
        finally:
            if tarea is not None:
                tarea.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await tarea
            liberar()

    app = FastAPI(
        title="ApplyOps",
        version=__version__,
        description="Ofertas recolectadas y puntuadas. El clic de postular es humano.",
        lifespan=ciclo_de_vida,
    )
    app.state.contenedor = contenedor
    app.middleware("http")(middleware_correlacion)
    registrar_manejadores(app)
    app.include_router(salud.router)
    app.include_router(ofertas.router)
    app.include_router(recolecciones.router)
    return app
