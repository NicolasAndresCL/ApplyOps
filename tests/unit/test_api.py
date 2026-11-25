"""API HTTP con el contenedor armado con fakes: contrato de respuestas y errores.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from applyops import __version__
from applyops.application.recolectar import RecolectarOfertas
from applyops.domain.errores import ApplyOpsError, RecoleccionEnCursoError
from applyops.main import crear_app
from tests.fakes import (
    AHORA,
    FuenteFalsa,
    RepoEnMemoria,
    contenedor_de_prueba,
    un_perfil,
    una_oferta,
)


def _app(repo: RepoEnMemoria, fuentes: list[FuenteFalsa] | None = None) -> FastAPI:
    recolectar = RecolectarOfertas(fuentes or [], repo, un_perfil(), reloj=lambda: AHORA)
    return crear_app(contenedor_de_prueba(repo, recolectar=recolectar))


@pytest.fixture
def repo() -> RepoEnMemoria:
    return RepoEnMemoria()


@pytest.fixture
def cliente(repo: RepoEnMemoria) -> Iterator[TestClient]:
    fuente = FuenteFalsa(
        "falsa",
        {
            "python": [
                una_oferta(),
                una_oferta(id_externo="2", titulo="Ventas Python"),  # descartada
                una_oferta(
                    id_externo="3", descripcion="Figma", sueldo_max_usd=None, sueldo_min_usd=None
                ),
            ]
        },
    )
    with TestClient(_app(repo, [fuente]), raise_server_exceptions=False) as c:
        yield c


def test_health(cliente: TestClient) -> None:
    assert cliente.get("/health").json() == {"estado": "ok", "version": __version__}


def test_ready_ok_y_degradado() -> None:
    with TestClient(_app(RepoEnMemoria(disponible=True))) as c:
        assert c.get("/ready").status_code == 200
    with TestClient(_app(RepoEnMemoria(disponible=False))) as c:
        respuesta = c.get("/ready")
    assert respuesta.status_code == 503
    assert respuesta.json() == {"estado": "degradado", "base_de_datos": False}


def test_recolectar_y_listar_priorizado(cliente: TestClient) -> None:
    resumen = cliente.post("/recolecciones").json()
    assert resumen["total_nuevas"] == 3
    assert resumen["resultados"] == [
        {"fuente": "falsa", "encontradas": 3, "nuevas": 3, "error": None, "vencidas": 0}
    ]

    bandeja = cliente.get("/ofertas").json()
    assert [o["clave"] for o in bandeja] == ["falsa:1", "falsa:3"]
    assert bandeja[0]["puntaje"] > bandeja[1]["puntaje"]

    con_descartadas = cliente.get("/ofertas", params={"incluir_descartadas": True}).json()
    assert len(con_descartadas) == 3


def test_filtros_validados(cliente: TestClient) -> None:
    cliente.post("/recolecciones")
    assert len(cliente.get("/ofertas", params={"min_puntaje": 90}).json()) == 1
    assert len(cliente.get("/ofertas", params={"limite": 1}).json()) == 1
    assert cliente.get("/ofertas", params={"min_puntaje": 101}).status_code == 422


def test_filtro_por_idioma(cliente: TestClient) -> None:
    cliente.post("/recolecciones")
    assert len(cliente.get("/ofertas", params={"idioma": "es"}).json()) == 2
    assert cliente.get("/ofertas", params={"idioma": "en"}).json() == []
    assert cliente.get("/ofertas", params={"idioma": "no_indica"}).json() == []
    rechazo = cliente.get("/ofertas", params={"idioma": "klingon"})
    assert rechazo.status_code == 422
    assert rechazo.json()["error"]["codigo"] == "entrada_invalida"


def test_detalle_trae_desglose(cliente: TestClient) -> None:
    cliente.post("/recolecciones")
    detalle = cliente.get("/ofertas/falsa:1").json()
    assert detalle["puntaje"] == 95
    assert [c["nombre"] for c in detalle["componentes"]] == [
        "stack",
        "modalidad",
        "sueldo",
        "seniority",
        "idioma",
    ]
    assert detalle["descripcion"].startswith("Buscamos")


def test_oferta_inexistente_responde_404_con_contrato_de_error(cliente: TestClient) -> None:
    respuesta = cliente.get("/ofertas/falsa:nope")
    assert respuesta.status_code == 404
    assert respuesta.json() == {
        "error": {"codigo": "oferta_no_encontrada", "mensaje": "No existe la oferta 'falsa:nope'"}
    }


def test_recoleccion_en_curso_responde_409(repo: RepoEnMemoria) -> None:
    class RecolectarOcupado(RecolectarOfertas):
        def ejecutar(self) -> object:  # type: ignore[override]
            raise RecoleccionEnCursoError

    ocupado = RecolectarOcupado([], repo, un_perfil(), reloj=lambda: AHORA)
    app = crear_app(contenedor_de_prueba(repo, recolectar=ocupado))
    with TestClient(app) as c:
        respuesta = c.post("/recolecciones")
    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["codigo"] == "recoleccion_en_curso"


def test_error_de_dominio_sin_mapeo_y_error_inesperado_son_500(repo: RepoEnMemoria) -> None:
    class RepoRoto(RepoEnMemoria):
        def __init__(self, error: Exception) -> None:
            super().__init__()
            self._error = error

        def listar(self, filtro: object) -> list[object]:  # type: ignore[override]
            raise self._error

    for error in (ApplyOpsError("x"), RuntimeError("detalle interno")):
        roto = RepoRoto(error)
        app = crear_app(contenedor_de_prueba(roto))
        with TestClient(app, raise_server_exceptions=False) as c:
            respuesta = c.get("/ofertas")
        assert respuesta.status_code == 500
        assert respuesta.json()["error"]["codigo"] == "error_interno"
        assert "detalle interno" not in respuesta.text, "el stack no sale al cliente"


def test_correlation_id_se_respeta_o_se_genera(cliente: TestClient) -> None:
    propio = cliente.get("/health", headers={"X-Correlation-ID": "n8n-123"})
    assert propio.headers["X-Correlation-ID"] == "n8n-123"

    invalido = cliente.get("/health", headers={"X-Correlation-ID": "id con espacios"})
    assert invalido.headers["X-Correlation-ID"] != "id con espacios"
    assert len(cliente.get("/health").headers["X-Correlation-ID"]) == 12


OFERTA_LINKEDIN = {
    "url": "https://www.linkedin.com/jobs/view/123/?trk=abc",
    "titulo": "Backend Engineer Python",
    "empresa": "Acme Remote",
    "descripcion": "Buscamos Python, FastAPI y PostgreSQL para equipo remoto en LATAM.",
    "modalidad": "remoto",
    "sueldo_min_usd": 2500,
    "sueldo_max_usd": 3500,
    "seniority": "semi_senior",
    "idioma": "en",
}


def test_registrar_oferta_manual_la_puntua_y_es_idempotente(cliente: TestClient) -> None:
    creada = cliente.post("/ofertas", json=OFERTA_LINKEDIN)
    assert creada.status_code == 201
    detalle = creada.json()
    assert detalle["fuente"] == "manual"
    assert detalle["clave"].startswith("manual:")
    assert detalle["puntaje"] > 80
    assert detalle["componentes"][0]["nombre"] == "stack"

    # Misma oferta con otro parámetro de rastreo: actualiza, no duplica.
    otra_copia = {
        **OFERTA_LINKEDIN,
        "url": "https://www.linkedin.com/jobs/view/123?refId=xyz",
        "titulo": "Backend Engineer Python (Sr)",
    }
    repetida = cliente.post("/ofertas", json=otra_copia).json()
    assert repetida["clave"] == detalle["clave"]
    assert repetida["titulo"] == "Backend Engineer Python (Sr)"
    assert len(cliente.get("/ofertas").json()) == 1


def test_registrar_oferta_manual_valida_con_el_contrato_de_error(cliente: TestClient) -> None:
    sin_url = cliente.post("/ofertas", json={**OFERTA_LINKEDIN, "url": "no-es-url"})
    assert sin_url.status_code == 422
    assert sin_url.json()["error"]["codigo"] == "entrada_invalida"
    assert "url" in sin_url.json()["error"]["mensaje"]

    invertido = cliente.post(
        "/ofertas", json={**OFERTA_LINKEDIN, "sueldo_min_usd": 5000, "sueldo_max_usd": 1000}
    )
    assert invertido.status_code == 422
    assert invertido.json()["error"]["codigo"] == "oferta_invalida"


def test_ruta_y_metodo_inexistentes_usan_el_contrato(cliente: TestClient) -> None:
    """Regresión (Sourcery, 2026-11-25): salían con `{"detail": ...}` de FastAPI."""
    ruta = cliente.get("/no-existe")
    assert ruta.status_code == 404
    assert ruta.json()["error"]["codigo"] == "ruta_no_encontrada"
    metodo = cliente.delete("/ofertas")
    assert metodo.status_code == 405
    assert metodo.json()["error"]["codigo"] == "metodo_no_permitido"


def test_error_de_dominio_sin_mapeo_no_filtra_su_mensaje(repo: RepoEnMemoria) -> None:
    """Regresión (Sourcery, 2026-11-25): el 500 devolvía str(error) al cliente."""

    class RepoQueFalla(RepoEnMemoria):
        def listar(self, filtro: object) -> list[object]:  # type: ignore[override]
            raise ApplyOpsError("ruta interna /srv/secreto y motivo crudo")

    roto = RepoQueFalla()
    with TestClient(crear_app(contenedor_de_prueba(roto)), raise_server_exceptions=False) as c:
        respuesta = c.get("/ofertas")
    assert respuesta.status_code == 500
    assert "secreto" not in respuesta.text
    assert respuesta.json()["error"]["mensaje"] == "Error interno; revisa los logs del servicio"


def test_http_exception_5xx_no_filtra_detalle_y_405_conserva_allow(repo: RepoEnMemoria) -> None:
    """Regresión (Sourcery, PR #5)."""
    from fastapi import HTTPException

    app = crear_app(contenedor_de_prueba(repo))

    @app.get("/roto")
    def roto() -> None:
        raise HTTPException(status_code=503, detail="host interno db-1:5432 caído")

    with TestClient(app) as c:
        respuesta = c.get("/roto")
        metodo = c.delete("/ofertas")
    assert respuesta.status_code == 503
    assert "db-1" not in respuesta.text
    assert respuesta.json()["error"]["codigo"] == "error_interno"
    assert "GET" in metodo.headers["allow"]
