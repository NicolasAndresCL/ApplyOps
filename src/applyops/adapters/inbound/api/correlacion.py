"""Middleware que asigna un `correlation_id` a cada request.

Respeta la cabecera `X-Correlation-ID` si el cliente la trae (así un flujo de
n8n o la UI pueden seguir su request en nuestros logs) y la devuelve siempre en
la respuesta.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from applyops.infra.logs import correlation_id, nuevo_correlation_id

CABECERA = "X-Correlation-ID"
# Solo ids razonables: una cabecera arbitraria terminaría escrita tal cual en los logs.
_ID_VALIDO = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")


async def middleware_correlacion(
    request: Request, siguiente: Callable[[Request], Awaitable[Response]]
) -> Response:
    recibido = request.headers.get(CABECERA, "")
    valor = recibido if _ID_VALIDO.match(recibido) else nuevo_correlation_id()
    token = correlation_id.set(valor)
    try:
        respuesta = await siguiente(request)
    finally:
        correlation_id.reset(token)
    respuesta.headers[CABECERA] = valor
    return respuesta
