"""Logs estructurados en JSON a stdout, con `correlation_id` por request o ciclo.

Cada línea es un objeto JSON con nivel, logger, mensaje, `correlation_id` y
los campos de `extra=`. Así una recolección o una request se siguen de punta a
punta filtrando por un solo id, y los logs se pueden consultar sin regex.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")

# Atributos que trae todo LogRecord; lo que no esté acá vino por `extra=`.
_ATRIBUTOS_ESTANDAR = frozenset(
    logging.LogRecord("", 0, "", 0, "", None, None).__dict__.keys() | {"message", "asctime"}
)


def nuevo_correlation_id() -> str:
    """Id corto y único para un ciclo o una request sin cabecera propia."""
    return uuid.uuid4().hex[:12]


class FormatoJson(logging.Formatter):
    """Serializa el registro como una línea JSON."""

    def format(self, record: logging.LogRecord) -> str:
        datos: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "nivel": record.levelname,
            "logger": record.name,
            "mensaje": record.getMessage(),
            "correlation_id": correlation_id.get(),
        }
        datos.update({k: v for k, v in record.__dict__.items() if k not in _ATRIBUTOS_ESTANDAR})
        if record.exc_info:
            datos["excepcion"] = self.formatException(record.exc_info)
        return json.dumps(datos, ensure_ascii=False, default=str)


def configurar_logs(nivel: str) -> None:
    """Reemplaza los handlers raíz por uno JSON a stdout. Idempotente."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(FormatoJson())
    raiz = logging.getLogger()
    raiz.handlers[:] = [handler]
    raiz.setLevel(nivel.upper())
    # httpx loguea cada request en INFO: ruido que tapa los logs propios.
    logging.getLogger("httpx").setLevel(logging.WARNING)
