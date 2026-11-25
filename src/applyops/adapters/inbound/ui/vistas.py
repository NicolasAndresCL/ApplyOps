"""Vistas NiceGUI de ApplyOps: bandeja, detalle, carga manual y ajustes.

`construir_raiz(cliente, assets)` devuelve la función raíz que recibe `ui.run`:
arma el layout (sidebar + header con los temas de Jaime) y enruta con
`ui.sub_pages`, así cada pestaña del navegador tiene su propia navegación y las
URLs sirven como enlace directo. Las dependencias (`cliente`, `marcar`, `assets`)
llegan a cada vista por `data=` de `ui.sub_pages`, que las inyecta por nombre de
parámetro; `marcar` es propio de cada cliente (resalta el menú y fija el título).

La UI no decide nada de negocio: todo sale de la API por `ClienteApi`. Ningún
botón postula: «Abrir la oferta» lleva al portal y el clic final es humano.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from nicegui import app, ui

from applyops.adapters.inbound.ui import temas
from applyops.adapters.inbound.ui.cliente import ApiNoDisponibleError, ApiRechazoError, ClienteApi

logger = logging.getLogger(__name__)

MODALIDADES = {
    "remoto": "Remoto",
    "remoto_local": "Remoto (ciertos países)",
    "hibrido": "Híbrido",
    "presencial": "Presencial",
    "desconocida": "No indica",
}
SENIORITIES = {
    "": "No indica",
    "sin_experiencia": "Sin experiencia",
    "junior": "Junior",
    "semi_senior": "Semi senior",
    "senior": "Senior",
    "experto": "Experto",
}
IDIOMAS = {"": "No indica", "es": "Español", "en": "Inglés", "pt": "Portugués"}
# Opciones del filtro de la bandeja: "" = todas; `no_indica` es el valor que entiende la API.
FILTRO_IDIOMA = {
    "": "Todos",
    "es": "Español",
    "en": "Inglés",
    "pt": "Portugués",
    "no_indica": "No indica",
}
# Tramos de color del puntaje en la bandeja.
UMBRAL_ALTO = 75
UMBRAL_MEDIO = 50

NAV = (
    ("/", "inbox", "Bandeja"),
    ("/nueva", "add_link", "Cargar oferta"),
    ("/ajustes", "palette", "Ajustes"),
)

COLUMNAS: list[dict[str, Any]] = [
    {"name": "puntaje", "label": "Puntaje", "field": "puntaje", "sortable": True, "align": "left"},
    {"name": "titulo", "label": "Oferta", "field": "titulo", "align": "left"},
    {"name": "empresa", "label": "Empresa", "field": "empresa", "align": "left"},
    {"name": "modalidad", "label": "Modalidad", "field": "modalidad", "align": "left"},
    {"name": "sueldo", "label": "Sueldo (USD)", "field": "sueldo", "align": "left"},
    {"name": "seniority", "label": "Seniority", "field": "seniority", "align": "left"},
    {"name": "idioma", "label": "Idioma", "field": "idioma", "align": "left"},
    {"name": "fuente", "label": "Fuente", "field": "fuente", "align": "left"},
]


def tramo(puntaje: int) -> str:
    """Clase CSS del puntaje: alto, medio o bajo."""
    if puntaje >= UMBRAL_ALTO:
        return "alto"
    return "medio" if puntaje >= UMBRAL_MEDIO else "bajo"


def texto_sueldo(minimo: int | None, maximo: int | None) -> str:
    """Rango legible con separador de miles chileno, o «—» si no se publica."""
    if minimo is None and maximo is None:
        return "—"
    piso = minimo if minimo is not None else maximo
    tope = maximo if maximo is not None else minimo

    def a_texto(n: int | None) -> str:
        return f"{n:,}".replace(",", ".")

    return a_texto(piso) if piso == tope else f"{a_texto(piso)}–{a_texto(tope)}"


def fila_bandeja(oferta: dict[str, Any]) -> dict[str, Any]:
    """Oferta de la API → fila de la tabla (textos ya legibles)."""
    return {
        "clave": oferta["clave"],
        "puntaje": oferta["puntaje"],
        "tramo": tramo(oferta["puntaje"]),
        "titulo": oferta["titulo"],
        "empresa": oferta["empresa"],
        "modalidad": MODALIDADES.get(oferta["modalidad"], oferta["modalidad"]),
        "sueldo": texto_sueldo(oferta["sueldo_min_usd"], oferta["sueldo_max_usd"]),
        "seniority": SENIORITIES.get(oferta["seniority"] or "", "No indica"),
        "idioma": IDIOMAS.get(oferta.get("idioma") or "", oferta.get("idioma") or ""),
        "fuente": oferta["fuente"],
        "descarte": oferta["descarte"],
    }


def entrada_desde_formulario(f: dict[str, Any]) -> dict[str, Any]:
    """Valores del formulario → cuerpo de `POST /ofertas` (vacíos → None, números → int)."""

    def entero(valor: Any) -> int | None:
        return int(valor) if valor not in (None, "") else None

    return {
        "url": (f.get("url") or "").strip(),
        "titulo": (f.get("titulo") or "").strip(),
        "empresa": (f.get("empresa") or "").strip(),
        "descripcion": (f.get("descripcion") or "").strip(),
        "modalidad": f.get("modalidad") or "desconocida",
        "paises": [p.strip() for p in (f.get("paises") or "").split(",") if p.strip()],
        "sueldo_min_usd": entero(f.get("sueldo_min_usd")),
        "sueldo_max_usd": entero(f.get("sueldo_max_usd")),
        "seniority": f.get("seniority") or None,
        "idioma": f.get("idioma") or None,
    }


def construir_raiz(cliente: ClienteApi, assets: temas.AssetsTema) -> Callable[[], None]:
    """Función raíz para `ui.run`: layout común + sub-páginas."""

    def raiz() -> None:
        tema = temas.resolver(app.storage.user.get("tema"))
        ui.add_head_html(f'<style id="ao-tema">{temas.css_del_tema(tema, assets)}</style>')
        ui.dark_mode(True)
        aplicar_colores(tema)
        nav: dict[str, ui.element] = {}

        with ui.row().classes("w-full no-wrap items-stretch").style("min-height:100vh; gap:0"):
            with ui.column().classes("ao-sidebar q-pa-md gap-1"):
                with ui.row().classes("items-center gap-2 q-pb-md"):
                    ui.icon("travel_explore", size="28px").classes("ao-accent")
                    ui.label("ApplyOps").classes("ao-marca text-xl text-weight-bold")
                for ruta, icono, texto in NAV:
                    with (
                        ui.row()
                        .classes("nav-item w-full items-center gap-3 q-px-md q-py-sm no-wrap")
                        .on("click", lambda r=ruta: ui.navigate.to(r))
                        .mark(f"nav{ruta}") as item
                    ):
                        ui.icon(icono).classes("nav-ico")
                        ui.label(texto).classes("nav-lbl")
                    nav[ruta] = item
                ui.space()
                ui.label("El clic de postular es tuyo.").classes("ao-mute text-caption q-pb-xl")

            with ui.column().classes("col").style("gap:0; min-width:0"):
                with ui.row().classes("ao-header w-full items-center q-px-lg").style("height:56px"):
                    titulo = ui.label("Bandeja").classes("ao-titulo text-h6")
                contenido = ui.column().classes("w-full q-pa-lg gap-4")

        def marcar(ruta: str | None, texto: str) -> None:
            for r, item in nav.items():
                item.classes(add="active") if r == ruta else item.classes(remove="active")
            titulo.text = texto

        with contenido:
            # `data=` inyecta las dependencias por nombre de parámetro en cada vista.
            ui.sub_pages(
                {
                    "/": vista_bandeja,
                    "/oferta/{clave}": vista_detalle,
                    "/nueva": vista_nueva,
                    "/ajustes": vista_ajustes,
                },
                data={"cliente": cliente, "marcar": marcar, "assets": assets},
            ).classes("w-full")

    return raiz


Marcar = Callable[[str | None, str], None]


def pildora(texto: str, icono: str) -> None:
    """Dato corto con icono, neutro: legible con cualquier acento (en Gear 5 es casi blanco)."""
    with ui.row().classes("ao-pildora items-center no-wrap gap-1"):
        ui.icon(icono, size="16px").classes("ao-accent")
        ui.label(texto)


def aplicar_colores(clave: str) -> None:
    """Colores de marca de Quasar desde la paleta: botones, barras y toggles toman el acento."""
    p = temas.PALETAS[temas.resolver(clave)]
    ui.colors(
        primary=p["accent"], secondary=p["accent2"], accent=p["accent2"], dark=p["bg"],
        positive=p["success"], negative=p["error"], warning=p["warning"], info=p["accent2"],
    )  # fmt: skip


def tarjeta_error(mensaje: str, reintentar: Callable[[], Awaitable[None]]) -> None:
    with ui.card().classes("ao-card w-full q-pa-lg"):
        ui.label("No se pudo hablar con la API").classes("text-h6")
        ui.label(mensaje).classes("ao-dim")
        ui.button("Reintentar", icon="refresh", on_click=reintentar).classes("ao-btn")


async def vista_bandeja(cliente: ClienteApi, marcar: Marcar) -> None:
    marcar("/", "Bandeja")
    filtros: dict[str, Any] = {"min_puntaje": 0, "incluir_descartadas": False, "idioma": ""}

    async def cargar() -> None:
        lista.clear()
        try:
            ofertas = await cliente.listar_ofertas(
                min_puntaje=filtros["min_puntaje"],
                incluir_descartadas=filtros["incluir_descartadas"],
                idioma=filtros["idioma"] or None,
            )
        except ApiNoDisponibleError as error:
            with lista:
                tarjeta_error(str(error), cargar)
            return
        with lista:
            if not ofertas and filtros["idioma"]:
                # Con el filtro de idioma puesto, «recolecta» sería un consejo equivocado.
                with ui.card().classes("ao-card w-full q-pa-lg").mark("sin-coincidencias"):
                    ui.label("Ninguna oferta pide ese idioma").classes("text-h6")
                    ui.label("Cambia el filtro de idioma o baja el puntaje mínimo.").classes(
                        "ao-dim"
                    )
                return
            if not ofertas:
                with ui.card().classes("ao-card w-full q-pa-lg").mark("bandeja-vacia"):
                    ui.label("Aún no hay ofertas").classes("text-h6")
                    ui.label(
                        "Pulsa «Recolectar ahora» o carga a mano una oferta de LinkedIn o Indeed."
                    ).classes("ao-dim")
                return
            with ui.card().classes("ao-card w-full q-pa-sm"):
                ui.label(f"{len(ofertas)} ofertas, de mayor a menor puntaje").classes(
                    "ao-dim q-px-sm"
                )
                tabla = (
                    ui.table(
                        columns=COLUMNAS,
                        rows=[fila_bandeja(o) for o in ofertas],
                        row_key="clave",
                        pagination=25,
                    )
                    .classes("w-full")
                    .mark("tabla-ofertas")
                )
                tabla.add_slot(
                    "body-cell-puntaje",
                    '<q-td :props="props"><span :class="\'ao-puntaje \' + props.row.tramo">'
                    "{{ props.value }}</span></q-td>",
                )
                tabla.add_slot(
                    "body-cell-titulo",
                    '<q-td :props="props"><div class="text-weight-medium">{{ props.value }}</div>'
                    '<div v-if="props.row.descarte" class="ao-mute text-caption">'
                    "Descartada: {{ props.row.descarte }}</div></q-td>",
                )
                tabla.on("rowClick", lambda e: ui.navigate.to(f"/oferta/{e.args[1]['clave']}"))

    async def recolectar() -> None:
        boton.disable()
        boton.props("loading")
        try:
            resumen = await cliente.recolectar()
        except ApiRechazoError as error:
            ui.notify(error.mensaje, type="warning")
        except ApiNoDisponibleError as error:
            ui.notify(str(error), type="negative")
        else:
            caidas = [r["fuente"] for r in resumen["resultados"] if r["error"]]
            encontradas = sum(r["encontradas"] for r in resumen["resultados"])
            aviso = f"{resumen['total_nuevas']} nuevas de {encontradas} encontradas"
            if caidas:
                aviso += f" · sin respuesta: {', '.join(caidas)}"
            ui.notify(aviso, type="warning" if caidas else "positive")
            await cargar()
        finally:
            boton.enable()
            boton.props(remove="loading")

    async def cambiar(clave: str, valor: Any) -> None:
        filtros[clave] = valor
        await cargar()

    with ui.row().classes("w-full items-center gap-3"):
        boton = (
            ui.button("Recolectar ahora", icon="travel_explore", on_click=recolectar)
            .classes("ao-btn ao-btn-primary")
            .mark("recolectar")
        )
        ui.button(
            "Cargar oferta", icon="add_link", on_click=lambda: ui.navigate.to("/nueva")
        ).classes("ao-btn").props("outline")
        ui.space()
        ui.select(
            FILTRO_IDIOMA,
            value="",
            label="Idioma",
            on_change=lambda e: cambiar("idioma", e.value or ""),
        ).props("outlined dense options-dense").style("width:150px").mark("filtro-idioma")
        ui.label("Puntaje mínimo").classes("ao-dim")
        ui.slider(
            min=0, max=100, step=5, value=0,
            on_change=lambda e: cambiar("min_puntaje", int(e.value)),
        ).props("label-always").style("width:180px").mark("min-puntaje")  # fmt: skip
        ui.switch(
            "Ver descartadas", on_change=lambda e: cambiar("incluir_descartadas", bool(e.value))
        ).mark("ver-descartadas")
    # Después de los controles: si se crea antes, los botones quedan bajo la tabla.
    lista = ui.column().classes("w-full")
    await cargar()


async def vista_detalle(cliente: ClienteApi, marcar: Marcar, clave: str) -> None:
    marcar(None, "Oferta")
    try:
        o = await cliente.obtener_oferta(clave)
    except ApiRechazoError as error:
        with ui.card().classes("ao-card w-full q-pa-lg"):
            ui.label(error.mensaje).classes("text-h6")
            ui.button("Volver a la bandeja", on_click=lambda: ui.navigate.to("/")).classes("ao-btn")
        return
    except ApiNoDisponibleError as error:
        tarjeta_error(str(error), lambda: vista_detalle(cliente, marcar, clave))
        return
    marcar(None, o["empresa"])

    with ui.card().classes("ao-card w-full q-pa-lg"):
        with ui.row().classes("w-full items-start no-wrap gap-4"):
            with ui.column().classes("col gap-1"):
                ui.label(o["titulo"]).classes("ao-titulo text-h5")
                ui.label(o["empresa"]).classes("ao-dim text-subtitle1")
                with ui.row().classes("gap-2"):
                    pildora(MODALIDADES.get(o["modalidad"], o["modalidad"]), "place")
                    if o["paises"]:
                        pildora(", ".join(o["paises"]), "public")
                    pildora(SENIORITIES.get(o["seniority"] or "", "No indica"), "school")
                    pildora(
                        f"USD {texto_sueldo(o['sueldo_min_usd'], o['sueldo_max_usd'])}", "payments"
                    )
                    pildora(IDIOMAS.get(o.get("idioma") or "", "Idioma no indicado"), "translate")
                    pildora(o["fuente"], "source")
            with ui.column().classes("items-center gap-0"):
                ui.label(str(o["puntaje"])).classes(f"ao-puntaje {tramo(o['puntaje'])} text-h4")
                ui.label("de 100").classes("ao-mute text-caption")
        if o["descarte"]:
            ui.label(f"Descartada: {o['descarte']}").classes("text-warning text-weight-medium")
        if o.get("vencida_en"):
            ui.label(
                "Ya no aparece en su fuente: probablemente se cerró. Verifícalo antes de postular."
            ).classes("text-warning text-weight-medium").mark("aviso-vencida")
        with ui.row().classes("items-center gap-3"):
            ui.button(
                "Abrir la oferta para postular", icon="open_in_new",
                on_click=lambda: ui.navigate.to(o["url"], new_tab=True),
            ).classes("ao-btn ao-btn-primary").mark("abrir-oferta")  # fmt: skip
            ui.button("Volver", icon="arrow_back", on_click=lambda: ui.navigate.to("/")).classes(
                "ao-btn"
            ).props("flat")
            ui.label("ApplyOps no postula por ti: el clic final es tuyo.").classes("ao-mute")

    with ui.card().classes("ao-card w-full q-pa-lg").mark("desglose"):
        ui.label("Por qué este puntaje").classes("ao-titulo text-h6")
        for c in o["componentes"]:
            with ui.row().classes("w-full items-center no-wrap gap-3"):
                ui.label(c["nombre"].capitalize()).style("width:90px").classes("text-weight-medium")
                ui.linear_progress(
                    value=c["puntos"] / c["maximo"] if c["maximo"] else 0, show_value=False
                ).props("rounded size=10px").classes("col")
                ui.label(f"{c['puntos']:g}/{c['maximo']:g}").style("width:64px").classes("ao-dim")
            ui.label(c["detalle"]).classes("ao-mute text-caption").style("margin-left:102px")

    with (
        ui.card().classes("ao-card w-full q-pa-md"),
        ui.expansion("Descripción completa", icon="description").classes("w-full"),
    ):
        ui.label(o["descripcion"]).style("white-space:pre-wrap").classes("ao-dim")


async def vista_nueva(cliente: ClienteApi, marcar: Marcar) -> None:
    marcar("/nueva", "Cargar oferta")
    f: dict[str, Any] = {"modalidad": "desconocida", "seniority": "", "idioma": ""}

    async def guardar() -> None:
        try:
            creada = await cliente.registrar_oferta(entrada_desde_formulario(f))
        except ApiRechazoError as error:
            ui.notify(error.mensaje, type="negative", multi_line=True)
            return
        except ApiNoDisponibleError as error:
            ui.notify(str(error), type="negative")
            return
        ui.notify(f"Guardada con puntaje {creada['puntaje']}", type="positive")
        ui.navigate.to(f"/oferta/{creada['clave']}")

    with ui.card().classes("ao-card w-full q-pa-lg"):
        ui.label("Oferta de un portal sin API").classes("ao-titulo text-h6")
        ui.label(
            "Copia la oferta desde LinkedIn, Indeed o Laborum. ApplyOps la puntúa igual que "
            "las recolectadas; la misma URL actualiza la oferta en vez de duplicarla."
        ).classes("ao-dim")
        with ui.grid(columns=2).classes("w-full gap-4"):
            ui.input("URL de la oferta *").bind_value(f, "url").props("outlined").mark("f-url")
            ui.input("Título *").bind_value(f, "titulo").props("outlined").mark("f-titulo")
            ui.input("Empresa *").bind_value(f, "empresa").props("outlined").mark("f-empresa")
            ui.input("Países (separados por coma)").bind_value(f, "paises").props("outlined")
            ui.select(MODALIDADES, label="Modalidad").bind_value(f, "modalidad").props("outlined")
            ui.select(SENIORITIES, label="Seniority").bind_value(f, "seniority").props("outlined")
            ui.number("Sueldo mínimo (USD/mes)", min=0).bind_value(f, "sueldo_min_usd").props(
                "outlined"
            )
            ui.number("Sueldo máximo (USD/mes)", min=0).bind_value(f, "sueldo_max_usd").props(
                "outlined"
            )
            ui.select(IDIOMAS, label="Idioma").bind_value(f, "idioma").props("outlined")
        ui.textarea("Descripción completa *").bind_value(f, "descripcion").props(
            "outlined autogrow"
        ).classes("w-full").mark("f-descripcion")
        ui.button("Guardar y puntuar", icon="calculate", on_click=guardar).classes(
            "ao-btn ao-btn-primary"
        ).mark("guardar")


async def vista_ajustes(cliente: ClienteApi, marcar: Marcar, assets: temas.AssetsTema) -> None:
    marcar("/ajustes", "Ajustes")
    actual = temas.resolver(app.storage.user.get("tema"))

    def elegir(clave: str) -> None:
        app.storage.user["tema"] = clave
        css = json.dumps(temas.css_del_tema(clave, assets))
        # Se reemplaza el <style> en vivo: cambiar de tema no recarga la página.
        ui.run_javascript(f"document.getElementById('ao-tema').innerHTML = {css};")
        aplicar_colores(clave)
        ui.notify(f"Tema: {temas.ETIQUETAS[clave]}", type="positive")
        for k, tarjeta in tarjetas.items():
            tarjeta.style(
                f"outline: {'3px solid ' + temas.PALETAS[k]['accent'] if k == clave else 'none'}"
            )

    ui.label("Tema").classes("ao-titulo text-h6")
    if not assets.disponibles:
        ui.label(
            "Sin las imágenes de los personajes: los temas se ven con sus colores. "
            "Impórtalas desde Jaime con scripts/importar_temas_jaime.ps1."
        ).classes("ao-mute")
    tarjetas: dict[str, ui.card] = {}
    with ui.grid(columns=2).classes("w-full gap-4"):
        for clave, etiqueta in temas.ETIQUETAS.items():
            p = temas.PALETAS[clave]
            with (
                ui.card()
                .classes("ao-card q-pa-md cursor-pointer")
                .style(f"outline: {'3px solid ' + p['accent'] if clave == actual else 'none'}")
                .on("click", lambda c=clave: elegir(c))
                .mark(f"tema-{clave}") as tarjeta
            ):
                ui.label(etiqueta).classes("text-weight-medium")
                with ui.row().classes("gap-2"):
                    for token in ("bg", "surface2", "accent", "accent2"):
                        ui.element("div").style(
                            f"width:28px;height:28px;border-radius:6px;background:{p[token]};"
                            "border:1px solid rgba(255,255,255,.18)"
                        )
            tarjetas[clave] = tarjeta

    estado = await cliente.estado()
    with ui.card().classes("ao-card w-full q-pa-md").mark("estado-api"):
        ui.label("Estado del servicio").classes("ao-titulo text-h6")
        ui.label(
            f"API: {'en línea' if estado['api'] else 'sin respuesta'}"
            + (f" · versión {estado['version']}" if estado["version"] else "")
        )
        ui.label(f"Base de datos: {'responde' if estado['base_de_datos'] else 'sin respuesta'}")
