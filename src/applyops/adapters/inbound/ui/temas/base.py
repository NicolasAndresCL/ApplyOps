"""CSS base parametrizado por la paleta, portado de `theme.build_css` de Jaime.

Las clases propias llevan prefijo `ao-` (en Jaime, `jaime-`). Incluye los
overrides de Quasar que en Jaime costaron tiempo: los diálogos y menús se
renderizan en un portal FUERA de `.nicegui-content`, así que sin reglas propias
quedan sin fondo; y los campos `outlined` sin fondo parecen texto suelto.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

from collections.abc import Mapping

# Todos los acentos son claros (dorado, blanco Nika, esmeralda, verde titán, cian): tinta oscura.
TINTA_SOBRE_ACENTO = "#14100A"
FUENTE = '"Segoe UI", Inter, system-ui, -apple-system, "Helvetica Neue", Arial, sans-serif'


def css_base(c: Mapping[str, str]) -> str:
    """Variables CSS, reset y estética común para la paleta `c`."""
    return f"""
:root {{
  --bg: {c["bg"]}; --surface: {c["surface"]}; --surface2: {c["surface2"]};
  --sidebar: {c["sidebar"]}; --border: {c["border"]}; --accent: {c["accent"]};
  --accent2: {c["accent2"]}; --text: {c["text"]}; --text-dim: {c["text_dim"]};
  --success: {c["success"]}; --warning: {c["warning"]}; --error: {c["error"]};
}}
html, body {{
  background: var(--bg) !important; color: var(--text);
  font-family: {FUENTE}; margin: 0; overflow-x: hidden;
}}
.nicegui-content {{
  background: var(--bg) !important; color: var(--text);
  padding: 0 !important; gap: 0 !important; width: 100%; max-width: 100%;
}}
.q-page, .q-layout, .q-page-container {{ background: var(--bg) !important; }}
::-webkit-scrollbar {{ width: 9px; height: 9px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: {c["border"]}; border-radius: 6px; }}
::-webkit-scrollbar-thumb:hover {{ background: {c["text_mute"]}; }}

.ao-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; }}
.ao-dim {{ color: var(--text-dim) !important; }}
.ao-mute {{ color: {c["text_mute"]} !important; }}
.ao-accent {{ color: var(--accent) !important; }}

/* Diálogos y menús: Quasar los pinta en un portal fuera de .nicegui-content. */
.q-dialog__backdrop {{ background: rgba(0,0,0,0.62) !important; }}
.q-dialog__inner {{ color: var(--text); }}
.q-dialog__inner > div {{ background: {c["surface"]}; border-radius: 12px; }}
.q-menu {{
  background: {c["surface2"]} !important; color: var(--text) !important;
  border: 1px solid var(--border);
}}
.q-menu .q-item {{ color: var(--text) !important; }}
.q-menu .q-item--active, .q-menu .q-item:hover {{ background: var(--surface) !important; }}

/* Campos outlined con fondo y borde legibles sobre las tarjetas. */
.q-field--outlined .q-field__control {{ background: {c["surface2"]} !important; border-radius: 8px; }}
.q-field--outlined .q-field__control:before {{ border: 1px solid {c["border"]} !important; }}
.q-field--outlined .q-field__control:hover:before {{ border-color: {c["text_mute"]} !important; }}
.q-field--outlined.q-field--focused .q-field__control:after {{ border: 2px solid {c["accent"]} !important; }}
.q-field__native, .q-field__input, .q-field__prefix, .q-field__suffix {{ color: {c["text"]} !important; }}
.q-field__label {{ color: {c["text_dim"]} !important; }}
.q-field__marginal, .q-field .q-icon {{ color: {c["text_dim"]} !important; }}
.q-checkbox__label, .q-toggle__label {{ color: {c["text"]} !important; }}
.q-chip {{ background: {c["surface"]} !important; color: {c["text"]} !important; }}

/* Tablas: transparentes sobre la tarjeta, filas con hover del acento. */
.q-table__container, .q-table__card, .q-table {{
  background: transparent !important; color: var(--text) !important; box-shadow: none !important;
}}
.q-table thead th {{ color: var(--text-dim) !important; font-weight: 600; }}
.q-table tbody tr {{ cursor: pointer; }}
.q-table tbody tr:hover {{ background: var(--surface2) !important; }}
.q-table td, .q-table th {{ border-color: var(--border) !important; }}
.q-linear-progress {{ color: var(--accent) !important; }}

/* Sidebar y navegación. */
.ao-sidebar {{
  width: 224px; flex: 0 0 auto; background: var(--sidebar);
  border-right: 1px solid var(--border); overflow-y: auto; overflow-x: hidden;
}}
.nav-item {{ border-radius: 10px; transition: background .12s ease; cursor: pointer; }}
.nav-item:hover {{ background: var(--surface2); }}
.nav-item.active {{ background: var(--accent); color: #fff; }}
.nav-item.active .nav-ico, .nav-item.active .nav-lbl {{ color: #fff !important; }}
.ao-header {{ background: var(--sidebar); border-bottom: 1px solid var(--border); }}

/* Botón principal: tinta oscura sobre el acento, también en los hijos (Quasar pinta la
   etiqueta en un <span> interno). `.q-btn.` sube la especificidad sobre `.text-white`:
   con Gear 5 (acento casi blanco) el texto quedaba invisible. */
.q-btn.ao-btn-primary, .q-btn.ao-btn-primary * {{ color: {TINTA_SOBRE_ACENTO} !important; font-weight: 700; }}

/* Píldoras de datos (detalle de la oferta): neutras, legibles con cualquier acento. */
.ao-pildora {{
  background: {c["surface2"]}; border: 1px solid {c["border"]}; color: {c["text"]};
  border-radius: 999px; padding: 3px 12px 3px 9px; font-size: 13px;
}}

/* Puntaje: color por tramo. */
.ao-puntaje {{ font-weight: 800; border-radius: 8px; padding: 2px 10px; display: inline-block; }}
.ao-puntaje.alto {{ background: {c["success"]}; color: #0A0F0C; }}
.ao-puntaje.medio {{ background: {c["warning"]}; color: #0A0F0C; }}
.ao-puntaje.bajo {{ background: {c["surface2"]}; color: {c["text_dim"]}; }}
"""
