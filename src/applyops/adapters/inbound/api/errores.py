"""Traducción central de errores del dominio a HTTP, uno por tipo.

Todo error sale con la misma forma `{"error": {"codigo", "mensaje"}}`; el
cliente distingue por `codigo`, no parseando el mensaje. Lo que no es un error
de dominio es un bug: 500 genérico hacia afuera y el stack completo en el log.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from applyops.domain.errores import (
    ApplyOpsError,
    OfertaInvalidaError,
    OfertaNoEncontradaError,
    RecoleccionEnCursoError,
)

logger = logging.getLogger(__name__)

ESTADOS: dict[type[ApplyOpsError], int] = {
    OfertaNoEncontradaError: 404,
    RecoleccionEnCursoError: 409,
    OfertaInvalidaError: 422,  # p. ej. sueldo mínimo mayor que el máximo
}


def _respuesta(codigo: str, mensaje: str, estado: int) -> JSONResponse:
    return JSONResponse({"error": {"codigo": codigo, "mensaje": mensaje}}, status_code=estado)


async def _error_dominio(_: Request, error: Exception) -> JSONResponse:
    estado = next((s for tipo, s in ESTADOS.items() if isinstance(error, tipo)), 500)
    if estado == 500:
        logger.error("Error de dominio sin código HTTP asignado", exc_info=error)
    codigo = error.codigo if isinstance(error, ApplyOpsError) else "error_interno"
    return _respuesta(codigo, str(error), estado)


async def _entrada_invalida(_: Request, error: Exception) -> JSONResponse:
    """422 de validación con la misma forma que el resto: el cliente no parsea dos formatos."""
    detalles = error.errors() if isinstance(error, RequestValidationError) else []
    partes = [
        f"{'.'.join(str(x) for x in d.get('loc', ())[1:]) or 'cuerpo'}: {d.get('msg', '')}"
        for d in detalles
    ]
    return _respuesta("entrada_invalida", "; ".join(partes) or "Entrada inválida", 422)


async def _error_inesperado(_: Request, error: Exception) -> JSONResponse:
    # Frontera declarada: el stack va al log, nunca al cliente.
    logger.error("Error no controlado", exc_info=error)
    return _respuesta("error_interno", "Error interno; revisa los logs del servicio", 500)


def registrar_manejadores(app: FastAPI) -> None:
    app.add_exception_handler(ApplyOpsError, _error_dominio)
    app.add_exception_handler(RequestValidationError, _entrada_invalida)
    app.add_exception_handler(Exception, _error_inesperado)
