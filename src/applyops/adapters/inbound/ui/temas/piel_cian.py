"""Piel Cian: la identidad visual del portafolio de Nicolás (tema por defecto de
`Portafolio-Frontend-React/src/themes/palettes.js`).

A diferencia de los temas de anime, no usa imágenes: todo es CSS puro, así que
se ve completo aunque no estén los assets de `assets/temas/`. Lo característico
del portafolio:

- **Fondo aurora**: tres degradados radiales (cian arriba a la izquierda, índigo
  arriba a la derecha, magenta abajo) fijos al hacer scroll.
- **Degradado de marca** cian → índigo → magenta en la marca, la línea del header
  y el título de cada vista (texto con `background-clip: text`).
- **Glow**: sombra cian difusa bajo las tarjetas y anillo de foco del acento.
- Títulos en Space Grotesk y números en JetBrains Mono; si no están instaladas
  caen a Segoe UI / Consolas (no se cargan desde un CDN).

**Nunca lanza**: ante cualquier error devuelve '' y el tema queda con sus colores.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

import logging
from collections.abc import Mapping

from applyops.adapters.inbound.ui.temas.assets import AssetsTema
from applyops.adapters.inbound.ui.temas.piel_op import rgb

logger = logging.getLogger(__name__)

TITULOS = "'Space Grotesk', 'Segoe UI', sans-serif"
MONO = "'JetBrains Mono', 'Fira Code', Consolas, Menlo, monospace"
# Magenta del degradado del portafolio: no es un token de la paleta (solo decora).
MAGENTA = "#E879F9"
# Texto sobre el cian (`onAccent` del portafolio): el blanco no se lee sobre #22D3EE.
TINTA_SOBRE_CIAN = "#04111A"


def piel_cian(tema: str, tokens: Mapping[str, str], assets: AssetsTema) -> str:
    """CSS de la piel Cian. No necesita assets: siempre devuelve la piel completa."""
    try:
        return _componer(tokens)
    except Exception:
        # Frontera declarada: una piel rota no puede dejar la UI sin tema.
        logger.warning("No se pudo construir la piel del tema", extra={"tema": tema}, exc_info=True)
        return ""


def _componer(t: Mapping[str, str]) -> str:
    cian, indigo, magenta = rgb(t["accent"]), rgb(t["accent2"]), rgb(MAGENTA)
    degradado = f"linear-gradient(110deg, {t['accent']} 0%, {t['accent2']} 50%, {MAGENTA} 100%)"
    aurora = (
        f"radial-gradient(1100px 600px at 12% -10%, rgba({cian},.16) 0%, transparent 60%),"
        f"radial-gradient(900px 520px at 95% 0%, rgba({indigo},.20) 0%, transparent 60%),"
        f"radial-gradient(900px 700px at 50% 115%, rgba({magenta},.10) 0%, transparent 70%)"
    )
    glow = f"0 0 0 1px {t['border']}, 0 18px 50px -18px rgba({cian},.32)"
    return f"""
/* ── Piel Cian (portafolio) ── */
html, body {{
  background-color: {t["bg"]} !important;
  background-image: {aurora} !important; background-attachment: fixed !important;
}}
.nicegui-content, .q-page, .q-layout, .q-page-container {{ background: transparent !important; }}

.ao-sidebar {{ background: rgba({rgb(t["sidebar"])},.78); border-right: 1px solid {t["border"]}; }}
.ao-header {{
  background: rgba({rgb(t["bg"])},.72); border-bottom: 1px solid transparent;
  border-image: {degradado} 1;
}}
.ao-marca, .ao-titulo.text-h6, .ao-header .ao-titulo {{
  background-image: {degradado}; -webkit-background-clip: text; background-clip: text;
  color: transparent !important;
}}
.ao-marca, .ao-titulo {{ font-family: {TITULOS}; letter-spacing: -.01em; }}

.ao-card {{
  background: linear-gradient(160deg, rgba({rgb(t["surface"])},.92), rgba({rgb(t["bg"])},.88));
  border: 1px solid {t["border"]}; border-radius: 14px; box-shadow: {glow};
  transition: box-shadow .2s ease, border-color .2s ease;
}}
.ao-card:hover {{ border-color: rgba({cian},.45); }}

.nav-item {{ border-radius: 10px; }}
.nav-item:hover {{ background: rgba({cian},.08); }}
.nav-item.active {{ background: {degradado}; box-shadow: 0 6px 22px -8px rgba({cian},.6); }}
.nav-item.active .nav-ico, .nav-item.active .nav-lbl {{
  color: {TINTA_SOBRE_CIAN} !important; font-weight: 700;
}}

.q-btn.ao-btn-primary {{ background: {degradado} !important; }}
.q-btn.ao-btn-primary, .q-btn.ao-btn-primary * {{ color: {TINTA_SOBRE_CIAN} !important; }}
.q-btn.ao-btn-primary:hover {{ box-shadow: 0 0 0 2px rgba({cian},.55); }}
.q-btn:focus-visible, .nav-item:focus-visible {{ box-shadow: 0 0 0 2px {t["accent"]} !important; }}

.ao-puntaje {{ font-family: {MONO}; }}
.q-table tbody tr:hover {{ background: rgba({cian},.07) !important; }}
.q-linear-progress {{ color: {t["accent"]} !important; }}
.ao-pildora {{ background: rgba({rgb(t["surface2"])},.85); }}
"""
