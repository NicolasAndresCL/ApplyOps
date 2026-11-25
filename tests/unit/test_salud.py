"""El endpoint de vida responde sin tocar dependencias.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from applyops import __version__
from applyops.main import crear_app


def test_health_responde_ok_con_la_version() -> None:
    cliente = TestClient(crear_app())
    respuesta = cliente.get("/health")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"estado": "ok", "version": __version__}
