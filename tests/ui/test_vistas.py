"""Recorridos de la UI con el `User` simulado de NiceGUI.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from nicegui import ui
from nicegui.testing import User
from nicegui.testing.user_simulation import user_simulation

from applyops.adapters.inbound.ui.cliente import ClienteApi
from applyops.adapters.inbound.ui.temas import AssetsTema
from applyops.adapters.inbound.ui.vistas import construir_raiz
from applyops.main import crear_app
from tests.fakes import FuenteFalsa, RepoEnMemoria, contenedor_de_prueba


def _filas(user: User) -> list[dict[str, object]]:
    tabla = next(iter(user.find(marker="tabla-ofertas").elements))
    assert isinstance(tabla, ui.table)
    return list(tabla.rows)


async def _esperar_filas(user: User, cantidad: int) -> list[dict[str, object]]:
    """Los filtros recargan la tabla en segundo plano: se espera a que llegue la nueva."""
    for _ in range(50):
        await user.should_see(marker="tabla-ofertas")
        filas = _filas(user)
        if len(filas) == cantidad:
            return filas
        await asyncio.sleep(0.02)
    raise AssertionError(f"La tabla nunca llegó a {cantidad} filas (tiene {len(filas)})")


async def test_bandeja_vacia_invita_a_recolectar(usuario: User) -> None:
    await usuario.open("/")
    await usuario.should_see("Aún no hay ofertas")
    await usuario.should_see(marker="recolectar")


async def test_recolectar_llena_la_bandeja_priorizada(usuario: User) -> None:
    await usuario.open("/")
    usuario.find(marker="recolectar").click()
    await usuario.should_see("3 nuevas de 3 encontradas")
    filas = _filas(usuario)
    # La descartada no se muestra por defecto; la mejor va primero.
    assert [f["clave"] for f in filas] == ["falsa:1", "falsa:3"]
    assert filas[0]["tramo"] == "alto"
    assert filas[0]["sueldo"] == "2.000–3.000"


async def test_ver_descartadas(usuario: User, repo: RepoEnMemoria) -> None:
    await usuario.open("/")
    usuario.find(marker="recolectar").click()
    await usuario.should_see("3 nuevas")
    usuario.find(marker="ver-descartadas").click()
    filas = await _esperar_filas(usuario, 3)
    assert filas[-1]["descarte"] == "El título contiene «ventas»"


async def test_filtro_de_idioma(usuario: User) -> None:
    await usuario.open("/")
    usuario.find(marker="recolectar").click()
    await usuario.should_see("3 nuevas")
    filtro = next(iter(usuario.find(marker="filtro-idioma").elements))
    assert isinstance(filtro, ui.select)
    filtro.value = "en"  # las ofertas falsas piden español
    await usuario.should_see("Ninguna oferta calza con los filtros")
    filtro.value = "es"
    filas = await _esperar_filas(usuario, 2)
    assert {f["idioma"] for f in filas} == {"Español"}


async def test_respuesta_vieja_no_pisa_el_filtro_actual(
    repo: RepoEnMemoria, fuente: FuenteFalsa, tmp_path: Path
) -> None:
    """Revisión Sourcery (PR #6): si cambias el filtro antes de que llegue la respuesta
    anterior, la respuesta vieja (más lenta) no debe reemplazar a la actual."""

    class ClienteLento(ClienteApi):
        async def listar_ofertas(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
            if kwargs.get("idioma") == "en":
                await asyncio.sleep(0.3)  # el pedido viejo llega después del nuevo
            return await super().listar_ofertas(*args, **kwargs)

    api = crear_app(contenedor_de_prueba(repo, [fuente]))
    cliente = ClienteLento("http://api", transporte=httpx.ASGITransport(app=api))
    async with user_simulation(root=construir_raiz(cliente, AssetsTema(tmp_path))) as usuario:
        await usuario.open("/")
        usuario.find(marker="recolectar").click()
        await usuario.should_see("3 nuevas")
        filtro = next(iter(usuario.find(marker="filtro-idioma").elements))
        assert isinstance(filtro, ui.select)
        filtro.value = "en"  # lento: queda esperando
        filtro.value = "es"  # rápido: es el vigente
        await _esperar_filas(usuario, 2)
        await asyncio.sleep(0.4)  # llega la respuesta vieja de «en»
        assert {f["idioma"] for f in await _esperar_filas(usuario, 2)} == {"Español"}
        await usuario.should_not_see("Ninguna oferta calza con los filtros")
    await cliente.cerrar()


async def test_ajustes_ofrece_el_tema_cian(usuario: User) -> None:
    await usuario.open("/ajustes")
    usuario.find(marker="tema-cian").click()
    await usuario.should_see("Tema: 💠 Cian · cian e índigo · Portafolio")


async def test_detalle_muestra_desglose_y_el_clic_es_humano(
    usuario: User, repo: RepoEnMemoria
) -> None:
    await usuario.open("/")
    usuario.find(marker="recolectar").click()
    await usuario.should_see("3 nuevas")
    await usuario.open("/oferta/falsa:1")
    await usuario.should_see("Backend Developer Python")
    await usuario.should_see("Por qué este puntaje")
    await usuario.should_see("Pide: Python, FastAPI, PostgreSQL, Docker")
    await usuario.should_see("ApplyOps no postula por ti: el clic final es tuyo.")
    await usuario.should_see(marker="abrir-oferta")


async def test_detalle_de_oferta_inexistente(usuario: User) -> None:
    await usuario.open("/oferta/falsa:nope")
    await usuario.should_see("No existe la oferta 'falsa:nope'")


async def test_cargar_oferta_manual_y_ver_su_puntaje(usuario: User, repo: RepoEnMemoria) -> None:
    await usuario.open("/nueva")
    usuario.find(marker="f-url").type("https://www.linkedin.com/jobs/view/999")
    usuario.find(marker="f-titulo").type("Backend Engineer Python")
    usuario.find(marker="f-empresa").type("Acme")
    usuario.find(marker="f-descripcion").type(
        "Equipo remoto que usa Python, FastAPI, PostgreSQL y Docker."
    )
    usuario.find(marker="guardar").click()
    await usuario.should_see("Guardada con puntaje")
    assert [p.oferta.fuente for p in repo.filas.values()] == ["manual"]
    await usuario.should_see("Por qué este puntaje")


async def test_cargar_oferta_invalida_muestra_el_error_de_la_api(
    usuario: User, repo: RepoEnMemoria
) -> None:
    await usuario.open("/nueva")
    usuario.find(marker="f-url").type("no-es-una-url")
    usuario.find(marker="guardar").click()
    await usuario.should_see("url:")
    assert repo.filas == {}


async def test_ajustes_cambia_el_tema_y_muestra_el_estado(usuario: User) -> None:
    await usuario.open("/ajustes")
    await usuario.should_see("⚡ Shingeki · verde titán · Eren")
    await usuario.should_see("versión")
    await usuario.should_see("Base de datos: responde")
    await usuario.should_see("Impórtalas desde Jaime")
    usuario.find(marker="tema-mugiwara").click()
    await usuario.should_see("Tema: 🏴‍☠️ Mugiwara · dorado · Luffy")


async def test_menu_navega(usuario: User) -> None:
    await usuario.open("/")
    usuario.find(marker="nav/nueva").click()
    await usuario.should_see("Oferta de un portal sin API")
    usuario.find(marker="nav/ajustes").click()
    await usuario.should_see("Estado del servicio")


async def test_sin_api_ofrece_reintentar(usuario_sin_api: User) -> None:
    await usuario_sin_api.open("/")
    await usuario_sin_api.should_see("No se pudo hablar con la API")
    await usuario_sin_api.should_see("Reintentar")
    await usuario_sin_api.open("/ajustes")
    await usuario_sin_api.should_see("API: sin respuesta")


async def test_oferta_vencida_avisa_en_el_detalle_y_sale_de_la_bandeja(
    usuario: User, repo: RepoEnMemoria
) -> None:
    await usuario.open("/")
    usuario.find(marker="recolectar").click()
    await usuario.should_see("3 nuevas")
    repo.marcar_vencidas("falsa", ["falsa:3"], datetime(2026, 11, 26, tzinfo=UTC))
    await usuario.open("/oferta/falsa:1")
    await usuario.should_see(marker="aviso-vencida")
    await usuario.open("/")
    filas = await _esperar_filas(usuario, 1)
    assert filas[0]["clave"] == "falsa:3"
