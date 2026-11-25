"""Fixtures de la UI: NiceGUI simulado hablando con la API REAL montada sobre fakes.

El `ClienteApi` de la UI usa `httpx.ASGITransport` contra la app FastAPI de
ApplyOps (con repositorio y fuentes en memoria): se prueba el contrato
UI → HTTP → API completo, sin red ni servidor.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from nicegui.testing import User
from nicegui.testing.user_simulation import user_simulation

from applyops.adapters.inbound.ui.cliente import ClienteApi
from applyops.adapters.inbound.ui.temas import AssetsTema
from applyops.adapters.inbound.ui.vistas import construir_raiz
from applyops.main import crear_app
from tests.fakes import FuenteFalsa, RepoEnMemoria, contenedor_de_prueba, una_oferta


@pytest.fixture
def repo() -> RepoEnMemoria:
    return RepoEnMemoria()


@pytest.fixture
def fuente() -> FuenteFalsa:
    return FuenteFalsa(
        "falsa",
        {
            "python": [
                una_oferta(),
                una_oferta(id_externo="2", titulo="Ventas Python"),  # descartada
                una_oferta(id_externo="3", descripcion="Figma", sueldo_min_usd=None,
                           sueldo_max_usd=None),
            ]
        },
    )  # fmt: skip


@pytest.fixture
async def usuario(repo: RepoEnMemoria, fuente: FuenteFalsa, tmp_path: Path) -> AsyncIterator[User]:
    api = crear_app(contenedor_de_prueba(repo, [fuente]))
    cliente = ClienteApi("http://api", transporte=httpx.ASGITransport(app=api))
    raiz = construir_raiz(cliente, AssetsTema(tmp_path / "sin-assets"))
    async with user_simulation(root=raiz) as user:
        yield user
    await cliente.cerrar()


@pytest.fixture
async def usuario_sin_api(tmp_path: Path) -> AsyncIterator[User]:
    """La API no responde: toda llamada falla con error de conexión."""

    def caida(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("conexión rechazada", request=request)

    cliente = ClienteApi("http://api", transporte=httpx.MockTransport(caida))
    async with user_simulation(root=construir_raiz(cliente, AssetsTema(tmp_path))) as user:
        yield user
    await cliente.cerrar()
