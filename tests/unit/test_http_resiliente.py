"""Política de reintentos del cliente HTTP, con transporte falso y sin esperas reales.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

from applyops.adapters.outbound.http_resiliente import ClienteHttpResiliente, crear_cliente
from applyops.domain.errores import FuenteNoDisponibleError

Manejador = Callable[[httpx.Request], httpx.Response]


def _cliente(
    respuestas: list[httpx.Response | Exception], intentos: int = 3
) -> tuple[ClienteHttpResiliente, list[float], list[httpx.Request]]:
    esperas: list[float] = []
    pedidos: list[httpx.Request] = []
    cola = list(respuestas)

    def manejar(request: httpx.Request) -> httpx.Response:
        pedidos.append(request)
        siguiente = cola.pop(0)
        if isinstance(siguiente, Exception):
            raise siguiente
        return siguiente

    http = httpx.Client(transport=httpx.MockTransport(manejar))
    cliente = ClienteHttpResiliente(
        http, "prueba", intentos=intentos, dormir=esperas.append, azar=lambda: 1.0
    )
    return cliente, esperas, pedidos


def test_devuelve_el_json() -> None:
    cliente, esperas, _ = _cliente([httpx.Response(200, json={"ok": True})])
    assert cliente.get_json("https://x.test/a") == {"ok": True}
    assert esperas == []


def test_reintenta_5xx_con_backoff_exponencial() -> None:
    cliente, esperas, pedidos = _cliente(
        [httpx.Response(503), httpx.Response(502), httpx.Response(200, json=[])]
    )
    assert cliente.get_json("https://x.test/a") == []
    assert len(pedidos) == 3
    assert esperas == [1.0, 2.0]  # azar=1.0 → backoff completo


def test_reintenta_timeout_y_error_de_red() -> None:
    cliente, _, pedidos = _cliente(
        [
            httpx.ReadTimeout("lento"),
            httpx.ConnectError("sin red"),
            httpx.Response(200, json={}),
        ]
    )
    assert cliente.get_json("https://x.test/a") == {}
    assert len(pedidos) == 3


def test_no_reintenta_un_4xx() -> None:
    cliente, esperas, pedidos = _cliente([httpx.Response(404)])
    with pytest.raises(FuenteNoDisponibleError, match="HTTP 404 \\(no se reintenta\\)"):
        cliente.get_json("https://x.test/a")
    assert len(pedidos) == 1
    assert esperas == []


def test_429_si_se_reintenta() -> None:
    cliente, _, pedidos = _cliente([httpx.Response(429), httpx.Response(200, json=1)])
    assert cliente.get_json("https://x.test/a") == 1
    assert len(pedidos) == 2


def test_agota_intentos_y_lanza_error_tipado() -> None:
    cliente, esperas, _ = _cliente([httpx.Response(500)] * 3)
    with pytest.raises(FuenteNoDisponibleError) as error:
        cliente.get_json("https://x.test/a")
    assert error.value.fuente == "prueba"
    assert error.value.motivo == "HTTP 500 tras 3 intentos"
    assert len(esperas) == 2, "no espera después del último intento"


def test_respuesta_que_no_es_json() -> None:
    cliente, _, _ = _cliente([httpx.Response(200, text="<html>mantención</html>")])
    with pytest.raises(FuenteNoDisponibleError, match="JSON"):
        cliente.get_json("https://x.test/a")


def test_intentos_debe_ser_positivo() -> None:
    with pytest.raises(ValueError, match="intentos"):
        ClienteHttpResiliente(httpx.Client(), "x", intentos=0)


def test_crear_cliente_fija_timeout_y_user_agent_sin_datos_personales() -> None:
    cliente = crear_cliente(7)
    assert cliente.timeout.read == 7
    assert cliente.headers["User-Agent"].startswith("ApplyOps/")
    cliente.close()
