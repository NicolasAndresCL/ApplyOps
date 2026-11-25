"""Cliente HTTP con timeout, reintentos con backoff exponencial + jitter y errores tipados.

Lo comparten todos los adaptadores de fuentes. Reglas:
- **Timeout siempre**: lo fija el `httpx.Client` que se inyecta (ver `crear_cliente`).
- **Reintentar solo lo transitorio**: 429, cualquier 5xx, timeouts y errores de red.
  Un 4xx distinto de 429 es un error nuestro (URL o parámetros malos): reintentarlo
  solo castiga a la fuente.
- **Respetar `Retry-After`** en 429/503: si la fuente pide esperar más que el
  backoff, se espera lo que pide (con tope), o los reintentos caen en la misma
  ventana de límite y se agotan en vano.
- **Tope de intentos**: al agotarlos se lanza `FuenteNoDisponibleError` y la
  recolección degrada esa fuente.
- **`dormir` inyectable**: los tests verifican el backoff sin esperar de verdad.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from applyops import __version__
from applyops.domain.errores import FuenteNoDisponibleError

logger = logging.getLogger(__name__)

# User-Agent genérico: identifica a la app sin datos personales.
USER_AGENT = f"ApplyOps/{__version__}"
# Backoff: 1 s, 2 s, 4 s… con tope, para no quedar esperando minutos en un ciclo.
BACKOFF_BASE_SEGUNDOS = 1.0
BACKOFF_MAXIMO_SEGUNDOS = 10.0
# 429 (límite de tasa) y toda la familia 5xx: fallas del lado de la fuente.
LIMITE_DE_TASA = 429
# Tope a lo que una fuente puede pedirnos esperar con Retry-After dentro de un ciclo.
RETRY_AFTER_MAXIMO_SEGUNDOS = 60.0


def es_transitorio(estado: int) -> bool:
    """¿Vale la pena reintentar este código HTTP?"""
    return estado == LIMITE_DE_TASA or 500 <= estado <= 599


def segundos_retry_after(valor: str | None, ahora: datetime | None = None) -> float | None:
    """Interpreta `Retry-After` (segundos o fecha HTTP). None si falta o no se entiende."""
    if not valor:
        return None
    valor = valor.strip()
    if valor.isdigit():
        return float(valor)
    try:
        fecha = parsedate_to_datetime(valor)
    except TypeError, ValueError:
        return None
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=UTC)
    return max(0.0, (fecha - (ahora or datetime.now(UTC))).total_seconds())


def crear_cliente(timeout_segundos: float) -> httpx.Client:
    """Cliente con timeout y User-Agent fijos; uno por proceso, reutiliza conexiones."""
    return httpx.Client(
        timeout=httpx.Timeout(timeout_segundos),
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        follow_redirects=True,
    )


class ClienteHttpResiliente:
    """GET de JSON con la política de reintentos descrita en el módulo."""

    def __init__(
        self,
        cliente: httpx.Client,
        fuente: str,
        intentos: int = 3,
        dormir: Callable[[float], None] = time.sleep,
        azar: Callable[[], float] = random.random,
    ) -> None:
        if intentos < 1:
            raise ValueError("intentos debe ser ≥ 1")
        self._cliente = cliente
        self._fuente = fuente
        self._intentos = intentos
        self._dormir = dormir
        self._azar = azar

    def get_json(self, url: str, params: Mapping[str, str | int] | None = None) -> Any:
        """Devuelve el JSON decodificado o lanza `FuenteNoDisponibleError`."""
        ultimo_motivo = "sin intentos"
        for intento in range(1, self._intentos + 1):
            pedido: float | None = None
            try:
                respuesta = self._cliente.get(url, params=params)
            except httpx.TimeoutException:
                ultimo_motivo = "timeout"
            except httpx.TransportError as error:
                ultimo_motivo = f"error de red: {type(error).__name__}"
            else:
                if es_transitorio(respuesta.status_code):
                    ultimo_motivo = f"HTTP {respuesta.status_code}"
                    pedido = segundos_retry_after(respuesta.headers.get("Retry-After"))
                elif respuesta.is_error:
                    raise FuenteNoDisponibleError(
                        self._fuente, f"HTTP {respuesta.status_code} (no se reintenta)"
                    )
                else:
                    return self._decodificar(respuesta)
            if intento < self._intentos:
                espera = self._espera(intento)
                if pedido is not None:
                    espera = max(espera, min(pedido, RETRY_AFTER_MAXIMO_SEGUNDOS))
                logger.warning(
                    "Fallo transitorio, se reintenta",
                    extra={
                        "fuente": self._fuente,
                        "intento": intento,
                        "motivo": ultimo_motivo,
                        "espera_s": round(espera, 2),
                    },
                )
                self._dormir(espera)
        raise FuenteNoDisponibleError(
            self._fuente, f"{ultimo_motivo} tras {self._intentos} intentos"
        )

    def _espera(self, intento: int) -> float:
        # Jitter completo: un número al azar entre 0 y el backoff exponencial, para
        # que varios clientes que fallaron juntos no reintenten todos al mismo tiempo.
        exponencial = min(BACKOFF_MAXIMO_SEGUNDOS, BACKOFF_BASE_SEGUNDOS * 2.0 ** (intento - 1))
        return float(exponencial * self._azar())

    def _decodificar(self, respuesta: httpx.Response) -> Any:
        try:
            return respuesta.json()
        except ValueError as error:
            raise FuenteNoDisponibleError(self._fuente, "respuesta no es JSON válido") from error
