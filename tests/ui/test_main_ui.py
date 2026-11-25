"""Composition root de la UI: configuración, montaje de assets y arranque de NiceGUI.

`ui.run` y `app.add_static_files` se interceptan: se verifica con qué se llaman
sin levantar un servidor.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pytest

from applyops.adapters.inbound.ui import main as ui_main


@pytest.fixture
def llamadas(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    registro: dict[str, Any] = {"estaticos": []}
    monkeypatch.setattr(ui_main.ui, "run", lambda raiz, **kw: registro.update(raiz=raiz, **kw))
    monkeypatch.setattr(
        ui_main.app,
        "add_static_files",
        lambda ruta, carpeta: registro["estaticos"].append((ruta, carpeta)),
    )
    monkeypatch.setattr(ui_main.app, "on_shutdown", lambda fn: registro.update(al_cerrar=fn))
    raiz_log = logging.getLogger()
    previos, nivel = raiz_log.handlers[:], raiz_log.level
    yield registro
    raiz_log.handlers[:] = previos
    raiz_log.setLevel(nivel)


def test_arranca_con_la_configuracion_del_entorno(
    llamadas: dict[str, Any], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "op").mkdir()
    monkeypatch.setenv("API_URL", "http://api:8000")
    monkeypatch.setenv("UI_HOST", "10.0.0.5")
    monkeypatch.setenv("UI_PUERTO", "9090")
    monkeypatch.setenv("UI_STORAGE_SECRET", "secreto-de-prueba-largo")
    monkeypatch.setenv("TEMAS_ASSETS_DIR", str(tmp_path))
    ui_main.iniciar()

    assert (llamadas["host"], llamadas["port"]) == ("10.0.0.5", 9090)
    assert llamadas["storage_secret"] == "secreto-de-prueba-largo"
    assert llamadas["reload"] is False and llamadas["show"] is False
    assert llamadas["estaticos"] == [("/temas", tmp_path)]
    assert callable(llamadas["raiz"]) and callable(llamadas["al_cerrar"])


def test_sin_assets_arranca_igual_y_lo_avisa(
    llamadas: dict[str, Any], monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:  # fmt: skip
    monkeypatch.setenv("TEMAS_ASSETS_DIR", str(tmp_path / "no-existe"))
    monkeypatch.delenv("UI_STORAGE_SECRET", raising=False)
    ui_main.iniciar()
    assert llamadas["estaticos"] == []
    assert len(llamadas["storage_secret"]) >= 16, "se genera un secreto si no viene"
    # configurar_logs deja un único handler JSON a stdout (caplog queda fuera).
    assert "Sin assets de temas" in capsys.readouterr().out


def test_secreto_vacio_de_compose_se_genera_y_uno_corto_se_rechaza(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UI_STORAGE_SECRET", "")
    assert len(ui_main.UiSettings().ui_storage_secret) >= ui_main.LARGO_MINIMO_SECRETO
    monkeypatch.setenv("UI_STORAGE_SECRET", "corto")
    with pytest.raises(ValueError, match="al menos 16"):
        ui_main.UiSettings()
