"""Oferta de trabajo normalizada, independiente de la fuente que la trajo.

Cada adaptador traduce el formato de su fuente a `Oferta`; el resto del sistema
(scoring, repositorio, API) solo conoce este modelo. Las invariantes se
validan al construir, así un dato roto falla en el adaptador que lo produjo y
no tres capas más adentro.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from applyops.domain.errores import OfertaInvalidaError


class Modalidad(StrEnum):
    """Dónde se trabaja. `REMOTO_LOCAL` es remoto pero restringido a ciertos países."""

    REMOTO = "remoto"
    REMOTO_LOCAL = "remoto_local"
    HIBRIDO = "hibrido"
    PRESENCIAL = "presencial"
    DESCONOCIDA = "desconocida"


class Seniority(StrEnum):
    """Nivel pedido por la oferta, en orden creciente."""

    SIN_EXPERIENCIA = "sin_experiencia"
    JUNIOR = "junior"
    SEMI_SENIOR = "semi_senior"
    SENIOR = "senior"
    EXPERTO = "experto"


@dataclass(frozen=True, slots=True)
class Oferta:
    """Una oferta tal como la publicó la fuente, ya normalizada.

    Los sueldos van en USD brutos mensuales; `None` significa que la oferta no
    lo publica (no que sea cero). `idioma` es un código ISO 639-1 o `None` si la
    fuente no lo especifica.
    """

    fuente: str
    id_externo: str
    titulo: str
    empresa: str
    url: str
    descripcion: str
    modalidad: Modalidad
    paises: tuple[str, ...] = ()
    sueldo_min_usd: int | None = None
    sueldo_max_usd: int | None = None
    seniority: Seniority | None = None
    idioma: str | None = None
    publicada_en: datetime | None = None

    def __post_init__(self) -> None:
        for campo in ("fuente", "id_externo", "titulo", "url"):
            if not getattr(self, campo).strip():
                raise OfertaInvalidaError(f"La oferta no tiene {campo}")
        for campo in ("sueldo_min_usd", "sueldo_max_usd"):
            valor = getattr(self, campo)
            if valor is not None and valor < 0:
                raise OfertaInvalidaError(f"{campo} negativo: {valor}")
        if (
            self.sueldo_min_usd is not None
            and self.sueldo_max_usd is not None
            and self.sueldo_min_usd > self.sueldo_max_usd
        ):
            raise OfertaInvalidaError(
                f"Sueldo invertido: mínimo {self.sueldo_min_usd} > máximo {self.sueldo_max_usd}"
            )

    @property
    def clave(self) -> str:
        """Clave natural e idempotente: la misma oferta recolectada dos veces no se duplica."""
        return f"{self.fuente}:{self.id_externo}"
