"""Endpoints de salud: `/health` (vivo) y `/ready` (listo), separados de verdad.

`/health` no toca dependencias, para que un orquestador no reinicie el
contenedor solo porque la base de datos está lenta. `/ready` sí verifica la
base: si no responde, devuelve 503 y el balanceador deja de mandar tráfico.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from applyops import __version__
from applyops.adapters.inbound.api.contenedor import Contenedor, obtener_contenedor

router = APIRouter(tags=["salud"])


@router.get("/health")
def health() -> dict[str, str]:
    """Vivo: el proceso responde. Nunca consulta dependencias externas."""
    return {"estado": "ok", "version": __version__}


@router.get("/ready", responses={503: {"description": "Alguna dependencia no responde"}})
def ready(contenedor: Annotated[Contenedor, Depends(obtener_contenedor)]) -> JSONResponse:
    """Listo: la base de datos responde."""
    base_ok = contenedor.repo.disponible()
    cuerpo = {"estado": "ok" if base_ok else "degradado", "base_de_datos": base_ok}
    return JSONResponse(cuerpo, status_code=200 if base_ok else 503)
