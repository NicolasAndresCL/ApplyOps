"""Infraestructura: logs JSON, recolección programada y composition root.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from applyops.application.recolectar import RecolectarOfertas
from applyops.domain.errores import RecoleccionEnCursoError
from applyops.infra.logs import FormatoJson, configurar_logs, correlation_id
from applyops.infra.programador import recolectar_periodicamente
from applyops.main import crear_app
from tests.fakes import AHORA, RepoEnMemoria, un_perfil

RAIZ = Path(__file__).parents[2]


def test_formato_json_incluye_extra_y_correlation_id() -> None:
    registro = logging.LogRecord(
        "applyops.x", logging.INFO, __file__, 1, "hola %s", ("mundo",), None
    )
    registro.fuente = "getonboard"
    token = correlation_id.set("abc123")
    try:
        linea = json.loads(FormatoJson().format(registro))
    finally:
        correlation_id.reset(token)
    assert linea["mensaje"] == "hola mundo"
    assert linea["nivel"] == "INFO"
    assert linea["correlation_id"] == "abc123"
    assert linea["fuente"] == "getonboard"


def test_formato_json_incluye_la_excepcion() -> None:
    try:
        raise ValueError("roto")
    except ValueError:
        import sys

        registro = logging.LogRecord("x", logging.ERROR, __file__, 1, "falló", (), sys.exc_info())
    assert "ValueError: roto" in json.loads(FormatoJson().format(registro))["excepcion"]


def test_configurar_logs_es_idempotente() -> None:
    raiz = logging.getLogger()
    previos, nivel = raiz.handlers[:], raiz.level
    try:
        configurar_logs("debug")
        configurar_logs("debug")
        assert len(raiz.handlers) == 1
        assert raiz.level == logging.DEBUG
    finally:
        raiz.handlers[:] = previos
        raiz.setLevel(nivel)


class _RecolectarContado(RecolectarOfertas):
    def __init__(self, errores: list[Exception]) -> None:
        super().__init__([], RepoEnMemoria(), un_perfil(), reloj=lambda: AHORA)
        self.llamadas = 0
        self._errores = errores

    def ejecutar(self):  # type: ignore[no-untyped-def]
        self.llamadas += 1
        if self._errores:
            raise self._errores.pop(0)
        return super().ejecutar()


def test_programador_sobrevive_a_errores_y_se_cancela_limpio() -> None:
    recolectar = _RecolectarContado([RuntimeError("bug"), RecoleccionEnCursoError()])

    async def correr() -> None:
        tarea = asyncio.create_task(recolectar_periodicamente(recolectar, 0.01))
        while recolectar.llamadas < 3:
            await asyncio.sleep(0.01)
        tarea.cancel()
        with pytest.raises(asyncio.CancelledError):
            await tarea

    asyncio.run(correr())
    assert recolectar.llamadas >= 3, "siguió corriendo tras un error y tras un ciclo ocupado"


def test_crear_app_desde_el_entorno_y_programador_en_lifespan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """El composition root real arranca con SQLite y el perfil de ejemplo."""
    shutil.copy(RAIZ / "perfil" / "busqueda.example.yaml", tmp_path / "busqueda.example.yaml")
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{tmp_path / 'x.db'}")
    monkeypatch.setenv("PERFIL_BUSQUEDA_PATH", str(tmp_path / "busqueda.yaml"))
    # Intervalo enorme: el primer ciclo corre al arrancar contra un puerto local
    # cerrado (sin salir a internet); la fuente falla y debe degradar sin tumbar la app.
    monkeypatch.setenv("RECOLECCION_INTERVALO_HORAS", "1000")
    monkeypatch.setenv("GETONBOARD_URL_BASE", "http://127.0.0.1:9")
    monkeypatch.setenv("HTTP_TIMEOUT_SEGUNDOS", "1")
    monkeypatch.setenv("HTTP_REINTENTOS", "1")
    raiz = logging.getLogger()
    previos, nivel = raiz.handlers[:], raiz.level
    try:
        with TestClient(crear_app()) as cliente:
            assert cliente.get("/health").status_code == 200
            # Tabla sin migrar: /ready responde igual (la consulta es SELECT 1).
            assert cliente.get("/ready").status_code == 200
    finally:
        raiz.handlers[:] = previos
        raiz.setLevel(nivel)
