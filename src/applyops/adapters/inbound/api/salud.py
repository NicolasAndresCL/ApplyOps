"""Endpoints de salud del servicio.

`/health` responde si el proceso está vivo: no toca dependencias, para que un
orquestador no reinicie el contenedor solo porque la base de datos está lenta.
Lo que depende de terceros va en `/ready`.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

from fastapi import APIRouter

from applyops import __version__

router = APIRouter(tags=["salud"])


@router.get("/health")
def health() -> dict[str, str]:
    """Vivo: el proceso responde. Nunca consulta dependencias externas."""
    return {"estado": "ok", "version": __version__}
