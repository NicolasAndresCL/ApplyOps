"""Piel de Eren (Shingeki no Kyojin), portada de `skins_equipo.py` de Jaime.

El único tema con tres capas de imagen: el titán de fondo (con un velo en
degradado que tapa donde vive el contenido y deja respirar la derecha), Eren de
figura y la viñeta del manga como emblema. Encima van sus efectos en CSS puro:
el aura verde del titán (que además separa la figura del fondo), el rayo ámbar
que lo invoca y el vapor que sube desde la base. Serif tallado (Cinzel), textura
de muro y esquinas casi duras.

**Nunca lanza**: ante cualquier error devuelve '' y el tema queda con sus colores.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

import logging
from collections.abc import Mapping

from applyops.adapters.inbound.ui.temas.assets import AssetsTema
from applyops.adapters.inbound.ui.temas.piel_op import fuentes, rgb

logger = logging.getLogger(__name__)

SERIF_TALLADO = "'Cinzel', 'Trajan Pro', 'Times New Roman', serif"
RADIO = "4px"


def piel_eren(tema: str, tokens: Mapping[str, str], assets: AssetsTema) -> str:
    """CSS de la piel de Eren, o '' si faltan las imágenes."""
    try:
        figura = assets.url("equipo/figuras/eren.png")
        emblema = assets.url("equipo/emblemas/eren.png")
        if not figura and not emblema:
            return ""
        return _componer(tokens, assets, figura, emblema)
    except Exception:
        # Frontera declarada: una piel rota no puede dejar la UI sin tema.
        logger.warning("No se pudo construir la piel del tema", extra={"tema": tema}, exc_info=True)
        return ""


def _componer(tokens: Mapping[str, str], assets: AssetsTema, figura: str, emblema: str) -> str:
    acento, acento2 = rgb(tokens["accent"]), rgb(tokens["accent2"])
    bgc, sup, sup2 = rgb(tokens["bg"]), rgb(tokens["surface"]), rgb(tokens["surface2"])
    vidrio = f"linear-gradient(158deg, rgba({sup},.82), rgba({bgc},.90))"
    lateral = f"linear-gradient(180deg, rgba({sup},.93), rgba({bgc},.97))"
    borde, borde_vivo = f"rgba({acento},.24)", f"rgba({acento},.48)"
    tinta_activa = "#0A0F0D"

    marca = (
        f"background-color: rgba({acento},1);"
        f"-webkit-mask:url({emblema}) center/contain no-repeat;"
        f"mask:url({emblema}) center/contain no-repeat;"
        if emblema
        else "display:none;"
    )
    muro = assets.url("equipo/tex/muro.png")
    capa_tex = (
        f"background-image:url({muro});background-size:420px;opacity:.24;mix-blend-mode:overlay;"
        if muro
        else "display:none;"
    )
    fondo = assets.url("equipo/fondos/eren.jpg")
    if fondo:
        velo = (
            f"linear-gradient(90deg, rgba({bgc},.93) 0%, rgba({bgc},.86) 42%, "
            f"rgba({bgc},.40) 78%, rgba({bgc},.22) 100%), "
        )
        capas_fondo = f"{velo}url({fondo}) center/cover no-repeat, "
    else:
        capas_fondo = ""
    capa_figura = (
        f"background:url({figura}) right bottom/contain no-repeat;" if figura else "display:none;"
    )
    return f"""
/* ═════════ eren · Shingeki ═════════ */
{fuentes(assets)}
html {{
  background:
    radial-gradient(120% 90% at 18% 6%, rgba({acento},.14) 0%, rgba({acento},0) 62%),
    radial-gradient(115% 105% at 50% 50%, rgba(0,0,0,0) 46%, rgba(0,0,0,.58) 100%),
    {capas_fondo}{tokens["bg"]} !important;
  background-attachment: fixed !important;
  background-size: {"auto, auto, auto, cover" if capas_fondo else "auto"} !important;
}}
body {{ background: transparent !important; }}
body::before {{ content:""; position:fixed; inset:0; z-index:-2; pointer-events:none; {capa_tex} }}
body::after {{
  content:""; position:fixed; z-index:-1; pointer-events:none;
  right:0; top:12vh; width:min(46vw,660px); height:min(62vh,640px);
  {capa_figura} opacity:.70;
  filter: drop-shadow(0 0 26px rgba({acento},.34)) drop-shadow(0 0 70px rgba({acento},.16));
  animation: eq-flotar 19s ease-in-out infinite, eren-aura 6.5s ease-in-out infinite;
}}
@keyframes eq-flotar {{
  0%,100% {{ transform: translateY(0) rotate(-2deg); }}
  50%     {{ transform: translateY(-20px) rotate(2deg); }}
}}
@keyframes eren-aura {{
  0%,100% {{ filter: drop-shadow(0 0 22px rgba({acento},.28)) drop-shadow(0 0 60px rgba({acento},.12)); }}
  50%     {{ filter: drop-shadow(0 0 40px rgba({acento},.46)) drop-shadow(0 0 96px rgba({acento},.22)); }}
}}
/* El rayo ámbar que invoca al titán: gradiente girado, sin asset. */
html::before {{
  content:""; position:fixed; inset:-20% -10%; z-index:-1; pointer-events:none;
  background: linear-gradient(104deg, transparent 44%, rgba({acento2},.16) 47%,
              rgba({acento2},.42) 49%, rgba({acento2},.16) 51%, transparent 55%);
  opacity:0; animation: eren-rayo 13s ease-in-out infinite;
}}
@keyframes eren-rayo {{
  0%, 86%, 100% {{ opacity:0; transform: translateX(0); }}
  88% {{ opacity:.85; transform: translateX(-1.5%); }} 90% {{ opacity:.15; }}
  92% {{ opacity:.70; transform: translateX(1%); }} 96% {{ opacity:0; }}
}}
/* Vapor que sube desde la base. */
html::after {{
  content:""; position:fixed; left:0; right:0; bottom:0; height:34vh; z-index:-1; pointer-events:none;
  background: radial-gradient(58% 100% at 72% 100%, rgba({acento},.13) 0%,
              rgba({acento},.05) 42%, transparent 74%);
  animation: eren-vapor 17s ease-in-out infinite;
}}
@keyframes eren-vapor {{
  0%,100% {{ transform: translateY(10px) scaleX(1); opacity:.55; }}
  50%     {{ transform: translateY(-14px) scaleX(1.12); opacity:.95; }}
}}
.nicegui-content, .q-page, .q-layout, .q-page-container {{ background: transparent !important; }}

.ao-sidebar {{
  background: {lateral} !important; backdrop-filter: blur(10px);
  border-right: 1px solid {borde} !important; position: relative;
}}
.ao-sidebar::after {{
  content:""; position:absolute; pointer-events:none; {marca}
  left:50%; bottom:14px; transform:translateX(-50%); width:120px; height:118px;
  opacity:.30; transition:opacity .25s ease;
}}
.ao-sidebar:hover::after {{ opacity:.56; }}
.ao-marca {{
  font-family:{SERIF_TALLADO} !important; letter-spacing:1px; font-size:22px !important;
  text-shadow: 0 2px 12px rgba({acento},.30);
}}
.ao-header {{
  background: {lateral} !important; backdrop-filter: blur(10px);
  border-bottom: none !important; position: relative;
}}
.ao-header::after {{
  content:""; position:absolute; left:0; right:0; bottom:0; height:3px;
  background: linear-gradient(90deg, rgba({acento2},1) 0%, rgba({acento},1) 42%, rgba({acento2},1) 100%);
  opacity:.85;
}}
.ao-titulo {{ font-family:{SERIF_TALLADO} !important; letter-spacing:1px; }}
.ao-card {{
  background: {vidrio} !important; border: 1px solid {borde} !important;
  border-radius: {RADIO} !important; backdrop-filter: blur(11px) saturate(1.06);
  box-shadow: 0 12px 34px rgba(0,0,0,.50); transition: border-color .2s ease, box-shadow .2s ease;
}}
.ao-card:hover {{
  border-color: {borde_vivo} !important;
  box-shadow: 0 12px 34px rgba(0,0,0,.50), 0 0 0 1px rgba({acento},.30),
              0 0 26px rgba({acento},.14) !important;
}}
.nav-item {{ position:relative; border-radius:{RADIO}; transition: background .15s ease, transform .15s ease; }}
.nav-item:hover {{ background: rgba({acento},.13) !important; transform: translateX(2px); }}
.nav-item.active {{
  background: linear-gradient(90deg, rgba({acento},1) 0%, rgba({acento},.86) 55%,
              rgba({acento2},.9) 165%) !important;
  box-shadow: 0 6px 18px rgba({acento},.30);
}}
.nav-item.active .nav-ico, .nav-item.active .nav-lbl {{ color:{tinta_activa} !important; font-weight:700; }}
.ao-btn {{ border-radius:{RADIO} !important; transition: transform .12s ease, box-shadow .18s ease; }}
.ao-btn:hover {{ transform: translateY(-1px); filter: brightness(1.05); }}
.q-btn.ao-btn-primary {{
  background: linear-gradient(135deg, rgba({acento},1) 0%, rgba({acento},.82) 100%) !important;
  color:{tinta_activa} !important; font-weight:700 !important;
  box-shadow: 0 4px 14px rgba({acento},.28); text-shadow: 0 0 12px rgba({acento},.45);
}}
.q-field--outlined .q-field__control {{ background: rgba({sup2},.64) !important; }}
.q-field--outlined .q-field__control:before {{ border-color: {borde} !important; }}
.q-chip {{ background: rgba({acento},.15) !important; border: 1px solid {borde}; }}
::-webkit-scrollbar-thumb {{
  background: linear-gradient(180deg, rgba({acento},.58), rgba({acento2},.46)) !important;
}}
::selection {{ background: rgba({acento},.32); }}
@media (prefers-reduced-motion: reduce) {{
  body::after, html::before, html::after {{ animation: none !important; }}
  html::before {{ opacity:.22; }}
  .ao-btn:hover, .nav-item:hover {{ transform: none; }}
}}
"""
