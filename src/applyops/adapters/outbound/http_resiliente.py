"""Cliente HTTP con timeout, reintentos con backoff exponencial + jitter y errores tipados.

Lo comparten todos los adaptadores de fuentes. Reglas:
- **Timeout siempre**: lo fija el `httpx.Client` que se inyecta (ver `crear_cliente`).
- **Reintentar solo lo transitorio**: 429, 5xx, timeouts y errores de red. Un 4xx
  distinto de 429 es un error nuestro (URL o parámetros malos): reintentarlo solo
  castiga a la fuente.
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
ESTADOS_TRANSITORIOS = frozenset({429, 500, 502, 503, 504})


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
            try:
                respuesta = self._cliente.get(url, params=params)
            except httpx.TimeoutException:
                ultimo_motivo = "timeout"
            except httpx.TransportError as error:
                ultimo_motivo = f"error de red: {type(error).__name__}"
            else:
                if respuesta.status_code in ESTADOS_TRANSITORIOS:
                    ultimo_motivo = f"HTTP {respuesta.status_code}"
                elif respuesta.is_error:
                    raise FuenteNoDisponibleError(
                        self._fuente, f"HTTP {respuesta.status_code} (no se reintenta)"
                    )
                else:
                    return self._decodificar(respuesta)
            if intento < self._intentos:
                espera = self._espera(intento)
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
