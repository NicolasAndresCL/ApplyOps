"""Piel One Piece (Mugiwara, Gear 5 y Zoro), portada de `skins_op.py` de Jaime.

Cada tema suma, sobre su paleta: la figura del personaje a la derecha (flotando),
su emblema al pie del sidebar (teñido con el acento por `mask-image`, o a color
si ya viene pintado), la cubierta de madera como TEXTURA teñida por
`mix-blend-mode: overlay`, cristal esmerilado, la cinta del sombrero bajo el
header y las tipografías Pirata One y Cinzel. Gear 5 y Zoro además despiertan el
Haki del Rey (relámpagos con remate propio: el destello de Nika, el corte de Zoro).

Todo lo que necesita imagen sale de `AssetsTema`; si falta, esa capa se omite.
**Nunca lanza**: ante cualquier error devuelve '' y el tema queda con sus colores.
Solo los temas oscuros se portaron (los cuatro de ApplyOps lo son).

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass

from applyops.adapters.inbound.ui.temas.assets import AssetsTema

logger = logging.getLogger(__name__)

# tema -> personaje (nombre del Jolly Roger en op/rogers/)
PERSONAJE = {"mugiwara": "luffy", "luffy_g5": "luffy", "esmeralda": "zoro"}
# La bandera de Mugiwara está pintada: teñirla con la máscara le saca lo que la hace buena.
EMBLEMA_COLOR = {"mugiwara": "op/mugiwara/skull.png", "luffy_g5": "op/mugiwara/skull.png"}
FONDO_PROPIO = {"mugiwara": "op/mugiwara/bg.jpg"}
TEXTURA_MADERA = "op/tex/madera.png"
OPACIDAD_FIGURA = {"mugiwara": 0.10}
FIGURA_FLOTANTE = {"mugiwara", "luffy_g5"}
# Luffy Gear 5 es apaisado (tumbado, riéndose): centrado en la franja útil.
POS_FLOTANTE = {
    "luffy_g5": "right:-40px; top:11vh; width:min(46vw,660px); height:min(54vh,520px);",
}


@dataclass(frozen=True, slots=True)
class Haki:
    """Haki del Rey: cuán fuerte, cada cuánto, con qué remate y qué PNG de relámpagos."""

    intensidad: float
    cada: str
    remate: str
    rayos: str


HAKI = {
    "luffy_g5": Haki(1.00, "11s", "nika", "op/tex/haki1.png"),
    "esmeralda": Haki(0.80, "14s", "corte", "op/tex/haki2.png"),
}

_REMATES = {
    # Nika: el fogonazo blanco del despertar del Gear 5.
    "nika": """
.ao-header::before {{
  content:""; position:fixed; inset:0; z-index:-1; pointer-events:none;
  background: radial-gradient(60% 45% at 72% 42%, rgba(255,255,255,.30) 0%, rgba(255,255,255,0) 68%);
  opacity:0; animation: haki-nika {cada} ease-out infinite;
}}
@keyframes haki-nika {{ 0%, 70%, 100% {{ opacity:0; }} 73% {{ opacity:{i_alta}; }} 78% {{ opacity:0; }} }}""",
    # El corte de Zoro: una línea fina y rapidísima, en diagonal.
    "corte": """
.ao-header::before {{
  content:""; position:fixed; inset:-15%; z-index:-1; pointer-events:none;
  background: linear-gradient(62deg, transparent 47.6%, rgba({acento},.85) 49.4%,
              rgba(255,255,255,.75) 50%, rgba({acento},.85) 50.6%, transparent 52.4%);
  opacity:0; animation: haki-corte {cada} ease-out infinite;
}}
@keyframes haki-corte {{
  0%, 74%, 100% {{ opacity:0; transform: translate(0,0); }}
  76% {{ opacity:{i_alta}; transform: translate(-2%, 2%); }}
  80% {{ opacity:0; transform: translate(2%, -2%); }}
}}""",
}


def rgb(hexa: str) -> str:
    """`#RRGGBB` → `r,g,b` para usar dentro de `rgba(...)`."""
    h = hexa.lstrip("#")
    return ",".join(str(int(h[i : i + 2], 16)) for i in (0, 2, 4))


def fuentes(assets: AssetsTema) -> str:
    """@font-face de Pirata One y Cinzel servidas localmente (sin CDN)."""
    css = ""
    for familia, archivo, peso in (
        ("Pirata One", "op/fuentes/pirata-one.woff2", 400),
        ("Cinzel", "op/fuentes/cinzel.woff2", 700),
    ):
        url = assets.url(archivo)
        if url:
            css += (
                f"@font-face{{font-family:'{familia}';font-style:normal;font-weight:{peso};"
                f"font-display:swap;src:url({url}) format('woff2');}}"
            )
    return css


def _haki(tema: str, acento: str, acento2: str, assets: AssetsTema) -> str:
    cfg = HAKI.get(tema)
    rayos = assets.url(cfg.rayos) if cfg else ""
    if not cfg or not rayos:
        return ""
    i = cfg.intensidad
    cada = cfg.cada
    remate = _REMATES[cfg.remate].format(
        acento=acento, acento2=acento2, cada=cada, i_alta=round(0.85 * i, 2)
    )
    return f"""
/* ── Haki del Rey: relámpagos negros con contorno del acento ── */
html::before {{
  content:""; position:fixed; inset:-10% -6%; z-index:-1; pointer-events:none;
  background:url({rayos}) center top/contain no-repeat;
  filter: drop-shadow(0 0 6px rgba({acento},.95)) drop-shadow(0 0 22px rgba({acento},.55))
          drop-shadow(0 0 44px rgba({acento2},.30));
  opacity:0; animation: haki-rayo {cada} steps(1, end) infinite;
}}
@keyframes haki-rayo {{
  0%, 62%, 100% {{ opacity:0; transform: scale(1) translateX(0); }}
  63% {{ opacity:{round(0.88 * i, 2)}; transform: scale(1.04) translateX(-.6%); }}
  64% {{ opacity:0.06; }}
  66% {{ opacity:{round(1.00 * i, 2)}; transform: scale(.98) translateX(.5%); }}
  67% {{ opacity:0.10; }}
  69% {{ opacity:{round(0.62 * i, 2)}; transform: scale(1.02) translateX(-.3%); }}
  71% {{ opacity:0; }}
}}
html::after {{
  content:""; position:fixed; inset:0; z-index:-1; pointer-events:none;
  background: radial-gradient(78% 70% at 68% 44%, rgba(0,0,0,0) 32%, rgba(6,4,8,.66) 100%);
  opacity:0; animation: haki-aire {cada} ease-in-out infinite;
}}
@keyframes haki-aire {{
  0%, 56%, 100% {{ opacity:0; }} 61% {{ opacity:{round(0.85 * i, 2)}; }}
  70% {{ opacity:{round(0.55 * i, 2)}; }} 78% {{ opacity:0; }}
}}
body::after {{ animation: op-flotar 18s ease-in-out infinite, haki-aura {cada} ease-out infinite; }}
@keyframes haki-aura {{
  0%, 60%, 100% {{ filter: none; }}
  66% {{ filter: drop-shadow(0 0 34px rgba({acento},{round(0.52 * i, 2)}))
                 drop-shadow(0 0 80px rgba(10,8,12,.55)); }}
  72% {{ filter: drop-shadow(0 0 16px rgba({acento},{round(0.22 * i, 2)})); }}
}}
{remate}
@media (prefers-reduced-motion: reduce) {{
  html::before, html::after, .ao-header::before {{ animation: none !important; opacity:0 !important; }}
  body::after {{ animation: none !important; filter: none !important; }}
}}
"""


def piel_op(tema: str, tokens: Mapping[str, str], assets: AssetsTema) -> str:
    """CSS de la piel One Piece del tema, o '' si no aplica o faltan los assets."""
    try:
        personaje = PERSONAJE.get(tema)
        if not personaje:
            return ""
        figura = assets.url(f"op/figuras/{tema}.png")
        emblema = assets.url(f"op/rogers/{personaje}.png")
        emblema_color = assets.url(EMBLEMA_COLOR.get(tema, ""))
        if not figura and not emblema and not emblema_color:
            return ""
        return _componer(tema, personaje, tokens, assets, figura, emblema, emblema_color)
    except Exception:
        # Frontera declarada: una piel rota no puede dejar la UI sin tema.
        logger.warning("No se pudo construir la piel del tema", extra={"tema": tema}, exc_info=True)
        return ""


def _componer(
    tema: str,
    personaje: str,
    tokens: Mapping[str, str],
    assets: AssetsTema,
    figura: str,
    emblema: str,
    emblema_color: str,
) -> str:
    acento, acento2 = rgb(tokens["accent"]), rgb(tokens["accent2"])
    bgc, sup = rgb(tokens["bg"]), rgb(tokens["surface"])
    sup2 = rgb(tokens["surface2"])
    vidrio = f"linear-gradient(158deg, rgba({sup},.80), rgba({bgc},.88))"
    vidrio_dlg = f"linear-gradient(158deg, rgba({sup},.97), rgba({bgc},.98))"
    lateral = f"linear-gradient(180deg, rgba({sup},.92), rgba({bgc},.96))"
    borde, borde_vivo = f"rgba({acento},.22)", f"rgba({acento},.45)"
    tinta_activa = "#1A1206"

    if emblema_color:
        marca = f"background:url({emblema_color}) center/contain no-repeat;"
    elif emblema:
        marca = (
            f"background-color: rgba({acento},1);"
            f"-webkit-mask:url({emblema}) center/contain no-repeat;"
            f"mask:url({emblema}) center/contain no-repeat;"
        )
    else:
        marca = "display:none;"

    img_fondo = assets.url(FONDO_PROPIO.get(tema, ""))
    fondo_propio = f"url({img_fondo}) center/cover no-repeat, " if img_fondo else ""
    madera = assets.url(TEXTURA_MADERA)
    capa_madera = (
        f"background-image:url({madera});background-size:400px;opacity:.30;mix-blend-mode:overlay;"
        if madera
        else "display:none;"
    )
    flotante = tema in FIGURA_FLOTANTE
    capa_figura = (
        f"background:url({figura}) {'center' if flotante else 'right bottom'}/contain no-repeat;"
        if figura
        else "display:none;"
    )
    figura_pos = (
        POS_FLOTANTE.get(
            tema, "right:-70px; top:56px; width:min(46vw,620px); height:min(72vh,600px);"
        )
        if flotante
        else "right:0; top:12vh; width:min(46vw,660px); height:min(62vh,640px);"
    )
    return f"""
/* ═════════ {tema} · {personaje} ═════════ */
{fuentes(assets)}
html {{
  background:
    radial-gradient(120% 90% at 18% 6%, rgba({acento},.16) 0%, rgba({acento},0) 62%),
    radial-gradient(115% 105% at 50% 50%, rgba(0,0,0,0) 46%, rgba(0,0,0,.55) 100%),
    {fondo_propio}{tokens["bg"]} !important;
  background-attachment: fixed !important;
  background-size: {"auto, auto, cover" if fondo_propio else "auto"} !important;
}}
body {{ background: transparent !important; }}
body::before {{ content:""; position:fixed; inset:0; z-index:-2; pointer-events:none; {capa_madera} }}
body::after {{
  content:""; position:fixed; z-index:-1; pointer-events:none;
  {figura_pos} {capa_figura}
  opacity:{OPACIDAD_FIGURA.get(tema, 0.52)};
  animation: op-flotar 18s ease-in-out infinite;
}}
@keyframes op-flotar {{
  0%,100% {{ transform: translateY(0) rotate(-2.5deg); }}
  50%     {{ transform: translateY(-22px) rotate(2.5deg); }}
}}
.nicegui-content, .q-page, .q-layout, .q-page-container {{ background: transparent !important; }}

.ao-sidebar {{
  background: {lateral} !important; backdrop-filter: blur(10px);
  border-right: 1px solid {borde} !important; position: relative;
}}
.ao-sidebar::after {{
  content:""; position:absolute; pointer-events:none; {marca}
  left:50%; bottom:14px; transform:translateX(-50%); width:126px; height:120px;
  opacity:.30; transition:opacity .25s ease;
}}
.ao-sidebar:hover::after {{ opacity:.55; }}
.ao-marca {{
  font-family:'Pirata One','Cinzel',"Segoe UI",serif !important;
  letter-spacing:.6px; font-size:26px !important; text-shadow: 0 2px 12px rgba({acento},.28);
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
.ao-titulo {{ font-family:'Cinzel','Segoe UI',serif !important; letter-spacing:.6px; }}

.ao-card {{
  background: {vidrio} !important; border: 1px solid {borde} !important;
  backdrop-filter: blur(11px) saturate(1.07); box-shadow: 0 12px 34px rgba(0,0,0,.48);
  transition: border-color .2s ease, box-shadow .2s ease;
}}
.ao-card:hover {{ border-color: {borde_vivo} !important; }}
.q-dialog .ao-card {{ background: {vidrio_dlg} !important; border: 1px solid {borde_vivo} !important; }}
.q-dialog__backdrop {{ background: rgba(0,0,0,.72) !important; }}
.q-menu {{ backdrop-filter: blur(8px); border: 1px solid {borde} !important; }}

.nav-item {{ position:relative; transition: background .15s ease, transform .15s ease; }}
.nav-item:hover {{ background: rgba({acento},.12) !important; transform: translateX(2px); }}
.nav-item.active {{
  background: linear-gradient(90deg, rgba({acento},1) 0%, rgba({acento},.86) 55%,
              rgba({acento2},.9) 165%) !important;
  box-shadow: 0 6px 18px rgba({acento},.28);
}}
.nav-item.active .nav-ico, .nav-item.active .nav-lbl {{ color:{tinta_activa} !important; font-weight:700; }}

.ao-btn {{ transition: transform .12s ease, box-shadow .18s ease, filter .18s ease; }}
.ao-btn:hover {{ transform: translateY(-1px); filter: brightness(1.04); }}
.q-btn.ao-btn-primary {{
  background: linear-gradient(135deg, rgba({acento},1) 0%, rgba({acento},.82) 100%) !important;
  color:{tinta_activa} !important; font-weight:700 !important;
  box-shadow: 0 4px 14px rgba({acento},.26);
}}
.q-btn.ao-btn-primary:hover {{ box-shadow: 0 8px 22px rgba({acento},.42); }}
.q-field--outlined .q-field__control {{ background: rgba({sup2},.62) !important; }}
.q-field--outlined .q-field__control:before {{ border-color: {borde} !important; }}
.q-chip {{ background: rgba({acento},.14) !important; border: 1px solid {borde}; }}
::-webkit-scrollbar-thumb {{
  background: linear-gradient(180deg, rgba({acento},.55), rgba({acento2},.45)) !important;
}}
::selection {{ background: rgba({acento},.30); }}
@media (prefers-reduced-motion: reduce) {{
  body::after {{ animation: none !important; }}
  .ao-btn:hover, .nav-item:hover {{ transform: none; }}
}}
{_haki(tema, acento, acento2, assets)}
"""
