"""Recolección periódica gestionada por el ciclo de vida de la app.

No es un `while True` suelto: es una tarea asyncio que arranca en el `lifespan`
de FastAPI y se cancela limpio al apagar. La recolección (bloqueante: httpx y
SQLAlchemy síncronos) corre en un hilo con `asyncio.to_thread` para no frenar
el event loop que atiende la API.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

import asyncio
import logging

from applyops.application.recolectar import RecolectarOfertas
from applyops.domain.errores import RecoleccionEnCursoError
from applyops.infra.logs import correlation_id, nuevo_correlation_id

logger = logging.getLogger(__name__)


async def recolectar_periodicamente(recolectar: RecolectarOfertas, intervalo_s: float) -> None:
    """Corre un ciclo al arrancar y luego uno cada `intervalo_s`, hasta ser cancelada."""
    while True:
        correlation_id.set(nuevo_correlation_id())
        try:
            await asyncio.to_thread(recolectar.ejecutar)
        except RecoleccionEnCursoError:
            logger.info("Ciclo programado omitido: ya hay una recolección manual en curso")
        except Exception:
            # Frontera declarada: un ciclo fallido se registra y el siguiente se
            # intenta igual; dejar morir la tarea apagaría la recolección en silencio.
            logger.exception("Ciclo de recolección falló")
        await asyncio.sleep(intervalo_s)
