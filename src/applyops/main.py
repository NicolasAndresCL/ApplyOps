"""Composition root de ApplyOps.

Es el único módulo que conoce las clases concretas: arma la aplicación
FastAPI y le conecta los routers. Uvicorn la levanta con
`uvicorn applyops.main:app`.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

from fastapi import FastAPI

from applyops import __version__
from applyops.adapters.inbound.api import salud


def crear_app() -> FastAPI:
    """Construye la app con sus routers."""
    app = FastAPI(
        title="ApplyOps",
        version=__version__,
        description="Ofertas recolectadas y puntuadas. El clic de postular es humano.",
    )
    app.include_router(salud.router)
    return app


app = crear_app()
