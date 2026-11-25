"""Endpoints de la bandeja de ofertas puntuadas.

Valida la entrada, llama al caso de uso y traduce a esquemas de salida. Cero
lógica de negocio: el orden y los filtros los resuelve el repositorio, el
puntaje viene calculado del scoring.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from applyops.adapters.inbound.api.contenedor import Contenedor, obtener_contenedor
from applyops.adapters.inbound.api.esquemas import (
    OfertaDetalleSalida,
    OfertaResumenSalida,
    RespuestaError,
)
from applyops.domain.puertos import FiltroOfertas

router = APIRouter(prefix="/ofertas", tags=["ofertas"])

ContenedorDep = Annotated[Contenedor, Depends(obtener_contenedor)]


@router.get("")
def listar_ofertas(
    contenedor: ContenedorDep,
    min_puntaje: Annotated[int, Query(ge=0, le=100)] = 0,
    incluir_descartadas: bool = False,
    limite: Annotated[int, Query(ge=1, le=500)] = 50,
) -> list[OfertaResumenSalida]:
    """Bandeja priorizada: mayor puntaje primero; a igual puntaje, la más reciente."""
    filtro = FiltroOfertas(
        min_puntaje=min_puntaje, incluir_descartadas=incluir_descartadas, limite=limite
    )
    return [OfertaResumenSalida.desde(p) for p in contenedor.consultar.listar(filtro)]


@router.get("/{clave}", responses={404: {"model": RespuestaError}})
def obtener_oferta(clave: str, contenedor: ContenedorDep) -> OfertaDetalleSalida:
    """Detalle con descripción y desglose del puntaje (qué sumó y qué no)."""
    return OfertaDetalleSalida.desde(contenedor.consultar.obtener(clave))
