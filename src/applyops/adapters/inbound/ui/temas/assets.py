"""Resolución de las imágenes y fuentes de los temas.

Las figuras de los personajes (Luffy, Zoro, Eren) y sus emblemas son imágenes
con derechos de autor: **no se versionan** (el repo es público). Viven en
`assets/temas/` (gitignored) y se copian desde Jaime con
`scripts/importar_temas_jaime.ps1`. Si un archivo falta, `url()` devuelve '' y
el tema se queda con sus colores planos: nada de esto puede romper la UI.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

RUTA_HTTP = "/temas"


@dataclass(frozen=True, slots=True)
class AssetsTema:
    """Carpeta local de assets y la ruta HTTP donde la UI la monta."""

    raiz: Path
    ruta_http: str = RUTA_HTTP

    @property
    def disponibles(self) -> bool:
        return self.raiz.is_dir()

    def url(self, relativa: str) -> str:
        """URL para `url(...)` en CSS, o '' si el archivo no está."""
        if not relativa or not (self.raiz / relativa).is_file():
            return ""
        return f"{self.ruta_http}/{relativa}"
