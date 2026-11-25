"""Cliente HTTP de la UI (errores tipados) y helpers de presentación.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

from applyops.adapters.inbound.ui.cliente import ApiNoDisponibleError, ApiRechazoError, ClienteApi
from applyops.adapters.inbound.ui.vistas import (
    entrada_desde_formulario,
    fila_bandeja,
    texto_sueldo,
    tramo,
)


def _cliente(manejar: Callable[[httpx.Request], httpx.Response]) -> ClienteApi:
    return ClienteApi("http://api", transporte=httpx.MockTransport(manejar))


async def test_error_de_contrato_se_traduce() -> None:
    cliente = _cliente(
        lambda r: httpx.Response(
            404, json={"error": {"codigo": "oferta_no_encontrada", "mensaje": "No"}}
        )
    )
    with pytest.raises(ApiRechazoError) as error:
        await cliente.obtener_oferta("x:1")
    assert (error.value.estado, error.value.codigo, error.value.mensaje) == (
        404, "oferta_no_encontrada", "No",
    )  # fmt: skip


async def test_error_sin_contrato() -> None:
    cliente = _cliente(lambda r: httpx.Response(400, text="<html>proxy</html>"))
    with pytest.raises(ApiRechazoError) as error:
        await cliente.listar_ofertas()
    assert error.value.codigo == "desconocido"


async def test_5xx_red_y_timeout_son_no_disponible() -> None:
    def timeout(r: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("lento", request=r)

    def red(r: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("nada", request=r)

    for manejar, texto in (
        (lambda r: httpx.Response(503), "HTTP 503"),
        (timeout, "a tiempo"),
        (red, "ConnectError"),
    ):
        with pytest.raises(ApiNoDisponibleError, match=texto):
            await _cliente(manejar).recolectar()


async def test_listar_envia_los_filtros() -> None:
    pedidos: list[httpx.Request] = []

    def manejar(r: httpx.Request) -> httpx.Response:
        pedidos.append(r)
        return httpx.Response(200, json=[])

    await _cliente(manejar).listar_ofertas(min_puntaje=60, incluir_descartadas=True, limite=10)
    assert dict(pedidos[0].url.params) == {
        "min_puntaje": "60", "incluir_descartadas": "true", "limite": "10",
    }  # fmt: skip


async def test_estado_con_base_caida() -> None:
    def manejar(r: httpx.Request) -> httpx.Response:
        if r.url.path == "/health":
            return httpx.Response(200, json={"estado": "ok", "version": "9.9.9"})
        return httpx.Response(503, json={"estado": "degradado"})

    assert await _cliente(manejar).estado() == {
        "api": True, "base_de_datos": False, "version": "9.9.9",
    }  # fmt: skip


@pytest.mark.parametrize(
    ("puntaje", "esperado"),
    [(100, "alto"), (75, "alto"), (74, "medio"), (50, "medio"), (49, "bajo"), (0, "bajo")],
)
def test_tramo(puntaje: int, esperado: str) -> None:
    assert tramo(puntaje) == esperado


@pytest.mark.parametrize(
    ("minimo", "maximo", "esperado"),
    [(None, None, "—"), (2000, 3000, "2.000–3.000"), (2500, None, "2.500"),
     (None, 1800, "1.800"), (2000, 2000, "2.000")],
)  # fmt: skip
def test_texto_sueldo(minimo: int | None, maximo: int | None, esperado: str) -> None:
    assert texto_sueldo(minimo, maximo) == esperado


def test_fila_bandeja_traduce_valores() -> None:
    fila = fila_bandeja({
        "clave": "g:1", "puntaje": 80, "titulo": "Dev", "empresa": "X", "modalidad": "hibrido",
        "sueldo_min_usd": None, "sueldo_max_usd": None, "seniority": None, "fuente": "g",
        "descarte": None,
    })  # fmt: skip
    assert (fila["modalidad"], fila["seniority"], fila["sueldo"], fila["tramo"]) == (
        "Híbrido", "No indica", "—", "alto",
    )  # fmt: skip


def test_entrada_desde_formulario_normaliza() -> None:
    entrada = entrada_desde_formulario({
        "url": " https://x.cl/1 ", "titulo": "Dev ", "empresa": "X", "descripcion": "texto",
        "modalidad": "", "paises": "Chile, , Perú", "sueldo_min_usd": 2000.0,
        "sueldo_max_usd": None, "seniority": "", "idioma": "en",
    })  # fmt: skip
    assert entrada == {
        "url": "https://x.cl/1", "titulo": "Dev", "empresa": "X", "descripcion": "texto",
        "modalidad": "desconocida", "paises": ["Chile", "Perú"], "sueldo_min_usd": 2000,
        "sueldo_max_usd": None, "seniority": None, "idioma": "en",
    }  # fmt: skip
