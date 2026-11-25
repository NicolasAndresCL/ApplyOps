"""Caso de uso: registrar a mano una oferta de un portal sin API (LinkedIn, Indeed, Laborum…).

Es la contracara de la decisión de no scrapear (ADR 0001): la persona copia la
oferta y ApplyOps la puntúa igual que a las recolectadas. La clave se deriva de
la URL normalizada, así cargar dos veces la misma oferta la actualiza en vez de
duplicarla.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit

from applyops.domain.oferta import Modalidad, Oferta, Seniority
from applyops.domain.perfil import PerfilBusqueda
from applyops.domain.puertos import RepoOfertas
from applyops.domain.scoring import OfertaPuntuada, puntuar

FUENTE_MANUAL = "manual"
# 16 hex = 64 bits de SHA-256: sin colisiones prácticas para una bandeja personal.
LARGO_ID = 16


@dataclass(frozen=True, slots=True)
class DatosOfertaManual:
    """Lo que la persona copia de la oferta. Solo URL, título, empresa y texto son obligatorios."""

    url: str
    titulo: str
    empresa: str
    descripcion: str
    modalidad: Modalidad = Modalidad.DESCONOCIDA
    paises: tuple[str, ...] = ()
    sueldo_min_usd: int | None = None
    sueldo_max_usd: int | None = None
    seniority: Seniority | None = None
    idioma: str | None = None


def id_desde_url(url: str) -> str:
    """Id estable para la URL: ignora mayúsculas del dominio, query, fragmento y `/` final.

    Los portales agregan parámetros de rastreo (`?trk=…`, `?refId=…`) que cambian en
    cada copia; sin normalizar, la misma oferta entraría dos veces.
    """
    partes = urlsplit(url.strip())
    normalizada = urlunsplit(
        (partes.scheme.lower(), partes.netloc.lower(), partes.path.rstrip("/"), "", "")
    )
    return hashlib.sha256(normalizada.encode()).hexdigest()[:LARGO_ID]


class RegistrarOfertaManual:
    """Construye la oferta, la puntúa con el perfil y la guarda."""

    def __init__(
        self, repo: RepoOfertas, perfil: PerfilBusqueda, reloj: Callable[[], datetime]
    ) -> None:
        self._repo = repo
        self._perfil = perfil
        self._reloj = reloj

    def ejecutar(self, datos: DatosOfertaManual) -> OfertaPuntuada:
        """Lanza `OfertaInvalidaError` si los datos violan las invariantes de `Oferta`."""
        ahora = self._reloj()
        oferta = Oferta(
            fuente=FUENTE_MANUAL,
            id_externo=id_desde_url(datos.url),
            titulo=datos.titulo.strip(),
            empresa=datos.empresa.strip(),
            url=datos.url.strip(),
            descripcion=datos.descripcion.strip(),
            modalidad=datos.modalidad,
            paises=tuple(p.strip() for p in datos.paises if p.strip()),
            sueldo_min_usd=datos.sueldo_min_usd,
            sueldo_max_usd=datos.sueldo_max_usd,
            seniority=datos.seniority,
            idioma=datos.idioma,
            publicada_en=ahora,
        )
        self._repo.guardar([OfertaPuntuada(oferta, puntuar(oferta, self._perfil), ahora)])
        return self._repo.obtener(oferta.clave)
