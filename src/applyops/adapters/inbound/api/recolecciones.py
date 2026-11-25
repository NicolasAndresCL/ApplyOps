"""Endpoint para lanzar una recolección a mano.

Es síncrono (`def`, corre en el threadpool de FastAPI): con una fuente tarda
segundos, y devolver el resumen en la misma respuesta es más útil que un id
para consultar después. Si hay otra corriendo responde 409.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from applyops.adapters.inbound.api.contenedor import Contenedor, obtener_contenedor
from applyops.adapters.inbound.api.esquemas import RespuestaError, ResumenRecoleccionSalida

router = APIRouter(prefix="/recolecciones", tags=["recolección"])


@router.post("", responses={409: {"model": RespuestaError}})
def recolectar(
    contenedor: Annotated[Contenedor, Depends(obtener_contenedor)],
) -> ResumenRecoleccionSalida:
    """Recorre todas las fuentes con las consultas del perfil y guarda lo nuevo, ya puntuado."""
    return ResumenRecoleccionSalida.desde(contenedor.recolectar.ejecutar())
