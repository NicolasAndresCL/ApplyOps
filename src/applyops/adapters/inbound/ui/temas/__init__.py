"""Temas visuales de ApplyOps: Mugiwara, Gear 5 (Luffy), Esmeralda (Zoro) y Shingeki (Eren).

Copiados de Jaime. `css_del_tema()` concatena el CSS base de la paleta con la
piel del tema (imágenes, tipografías, efectos); la piel va al final para pisar
la base sin duplicarla. Un tema desconocido cae al de por defecto.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from applyops.adapters.inbound.ui.temas.assets import AssetsTema
from applyops.adapters.inbound.ui.temas.base import css_base
from applyops.adapters.inbound.ui.temas.paletas import ETIQUETAS, PALETAS, TEMA_POR_DEFECTO
from applyops.adapters.inbound.ui.temas.piel_eren import piel_eren
from applyops.adapters.inbound.ui.temas.piel_op import piel_op

Piel = Callable[[str, Mapping[str, str], AssetsTema], str]

PIELES: dict[str, Piel] = {
    "mugiwara": piel_op,
    "luffy_g5": piel_op,
    "esmeralda": piel_op,
    "eren": piel_eren,
}

__all__ = ["ETIQUETAS", "PALETAS", "TEMA_POR_DEFECTO", "AssetsTema", "css_del_tema", "resolver"]


def resolver(clave: str | None) -> str:
    """La clave si existe; si no, el tema por defecto (p. ej. un valor viejo guardado)."""
    return clave if clave in PALETAS else TEMA_POR_DEFECTO


def css_del_tema(clave: str | None, assets: AssetsTema) -> str:
    """CSS completo del tema: base de la paleta + piel (si hay assets)."""
    tema = resolver(clave)
    tokens = PALETAS[tema]
    return css_base(tokens) + PIELES[tema](tema, tokens, assets)
