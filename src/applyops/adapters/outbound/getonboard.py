"""Adaptador de Get on Board (API pública v0, sin autenticación).

Endpoint: `GET /search/jobs?query=…&per_page=…&page=…&expand=["company","location_tenants"]`.
Contrato verificado contra respuestas reales el 2026-11-25 (fixtures en
`tests/fixtures/getonboard_*.json`):

- `remote_modality`: `fully_remote` | `remote_local` | `hybrid` | `no_remote`.
- `countries`: países, o `["Remote"]` en ofertas remotas (marcador, no país); en
  `remote_local` el país exigido viene en `location_tenants` expandido.
- `min_salary` / `max_salary`: USD brutos mensuales, o `null` si no se publica.
- `seniority.data.id`: 1 sin experiencia · 2 junior · 3 semi senior · 4 senior · 5 expert
  (catálogo `GET /seniorities`).
- `lang`: `es` | `en` | `lang_not_specified`.
- `published_at`: epoch en segundos.

Una oferta con forma inesperada se salta con un warning en vez de tumbar toda
la página: una oferta rara no debe dejar sin datos al resto.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

import html
import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

from applyops.adapters.outbound.http_resiliente import ClienteHttpResiliente
from applyops.domain.errores import FuenteNoDisponibleError, OfertaInvalidaError
from applyops.domain.oferta import Modalidad, Oferta, Seniority

logger = logging.getLogger(__name__)

NOMBRE = "getonboard"
URL_BASE = "https://www.getonbrd.com/api/v0"
POR_PAGINA = 50  # máximo que acepta la API por página
MAX_PAGINAS = 4  # 200 ofertas por consulta bastan; la API ordena por relevancia

MODALIDADES = {
    "fully_remote": Modalidad.REMOTO,
    "remote_local": Modalidad.REMOTO_LOCAL,
    "hybrid": Modalidad.HIBRIDO,
    "no_remote": Modalidad.PRESENCIAL,
}
SENIORITIES = {
    1: Seniority.SIN_EXPERIENCIA,
    2: Seniority.JUNIOR,
    3: Seniority.SEMI_SENIOR,
    4: Seniority.SENIOR,
    5: Seniority.EXPERTO,
}
# Valor que Get on Board pone en `countries` para ofertas remotas; no es un país.
MARCADOR_REMOTO = "Remote"
# Relaciones que se piden expandidas: el nombre de la empresa y los países de remote_local.
EXPANDIR = ["company", "location_tenants"]
# Campos de texto que se concatenan como descripción, en el orden en que se leen.
CAMPOS_TEXTO = ("description", "functions", "desirable", "projects", "benefits")


class FuenteGetOnBoard:
    """Implementa el puerto `FuenteOfertas` para Get on Board."""

    nombre = NOMBRE

    def __init__(
        self,
        http: ClienteHttpResiliente,
        url_base: str = URL_BASE,
        max_paginas: int = MAX_PAGINAS,
    ) -> None:
        self._http = http
        self._url = f"{url_base.rstrip('/')}/search/jobs"
        self._max_paginas = max_paginas

    def buscar(self, consulta: str) -> list[Oferta]:
        ofertas: list[Oferta] = []
        pagina = 1
        while pagina <= self._max_paginas:
            cuerpo = self._http.get_json(
                self._url,
                params={
                    "query": consulta,
                    "per_page": POR_PAGINA,
                    "page": pagina,
                    "expand": json.dumps(EXPANDIR),
                },
            )
            datos, total_paginas = _validar_pagina(cuerpo)
            ofertas.extend(o for o in map(_mapear_seguro, datos) if o is not None)
            if pagina >= total_paginas:
                break
            pagina += 1
        return ofertas


def _validar_pagina(cuerpo: Any) -> tuple[list[Any], int]:
    if not isinstance(cuerpo, dict) or not isinstance(cuerpo.get("data"), list):
        raise FuenteNoDisponibleError(NOMBRE, "respuesta sin la lista 'data': ¿cambió el contrato?")
    meta = cuerpo.get("meta") or {}
    total = meta.get("total_pages", 1)
    return cuerpo["data"], total if isinstance(total, int) else 1


def _mapear_seguro(item: Any) -> Oferta | None:
    try:
        return mapear_oferta(item)
    except (KeyError, TypeError, ValueError, OfertaInvalidaError) as error:
        id_item = item.get("id") if isinstance(item, dict) else None
        logger.warning(
            "Oferta con forma inesperada, se omite",
            extra={"fuente": NOMBRE, "id": id_item, "error": repr(error)},
        )
        return None


def mapear_oferta(item: dict[str, Any]) -> Oferta:
    """Traduce un elemento de `data` al modelo del dominio. Pura: testeable con el fixture."""
    atributos = item["attributes"]
    return Oferta(
        fuente=NOMBRE,
        id_externo=str(item["id"]),
        titulo=atributos["title"].strip(),
        empresa=_empresa(atributos),
        url=item.get("links", {}).get("public_url")
        or f"https://www.getonbrd.com/jobs/{item['id']}",
        descripcion=texto_plano(" ".join(atributos.get(c) or "" for c in CAMPOS_TEXTO)),
        modalidad=MODALIDADES.get(atributos.get("remote_modality") or "", Modalidad.DESCONOCIDA),
        paises=_paises(atributos),
        sueldo_min_usd=_entero_o_none(atributos.get("min_salary")),
        sueldo_max_usd=_entero_o_none(atributos.get("max_salary")),
        seniority=_seniority(atributos),
        idioma=_idioma(atributos.get("lang")),
        publicada_en=_fecha(atributos.get("published_at")),
    )


def texto_plano(contenido_html: str) -> str:
    """Quita etiquetas y entidades HTML y colapsa espacios."""
    sin_etiquetas = re.sub(r"<[^>]+>", " ", contenido_html)
    return re.sub(r"\s+", " ", html.unescape(sin_etiquetas)).strip()


def _empresa(atributos: dict[str, Any]) -> str:
    empresa = (atributos.get("company") or {}).get("data") or {}
    nombre = (empresa.get("attributes") or {}).get("name")
    return str(nombre) if nombre else str(empresa.get("id", "desconocida"))


def _paises(atributos: dict[str, Any]) -> tuple[str, ...]:
    """Países reales de la oferta.

    `countries` trae el marcador `"Remote"` en las ofertas remotas: no es un país.
    En `remote_local` la restricción real está en `location_tenants` (expandido).
    Bug real del 2026-11-25: leer `"Remote"` como país descartó 62 de 239 ofertas.
    """
    paises = [p for p in atributos.get("countries") or () if p != MARCADOR_REMOTO]
    if paises:
        return tuple(paises)
    tenants = (atributos.get("location_tenants") or {}).get("data") or []
    return tuple(
        str(t["attributes"]["name"])
        for t in tenants
        if isinstance(t, dict)
        and isinstance(t.get("attributes"), dict)
        and t["attributes"].get("name")
    )


def _seniority(atributos: dict[str, Any]) -> Seniority | None:
    dato = (atributos.get("seniority") or {}).get("data") or {}
    try:
        return SENIORITIES.get(int(dato["id"]))
    except KeyError, TypeError, ValueError:
        return None


def _idioma(lang: Any) -> str | None:
    return lang if lang in ("es", "en", "pt") else None


def _entero_o_none(valor: Any) -> int | None:
    return int(valor) if isinstance(valor, int | float) else None


def _fecha(epoch: Any) -> datetime | None:
    return datetime.fromtimestamp(epoch, tz=UTC) if isinstance(epoch, int | float) else None
