"""Temas copiados de Jaime: paletas, piel con y sin assets, y que nunca rompan la UI.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from applyops.adapters.inbound.ui import temas
from applyops.adapters.inbound.ui.temas.paletas import TOKENS
from applyops.adapters.inbound.ui.temas.piel_eren import piel_eren
from applyops.adapters.inbound.ui.temas.piel_op import piel_op, rgb

ASSETS_COMPLETOS = [
    "op/figuras/mugiwara.png", "op/figuras/luffy_g5.png", "op/figuras/esmeralda.png",
    "op/rogers/zoro.png", "op/mugiwara/skull.png", "op/mugiwara/bg.jpg",
    "op/tex/madera.png", "op/tex/haki1.png", "op/tex/haki2.png",
    "op/fuentes/pirata-one.woff2", "op/fuentes/cinzel.woff2",
    "equipo/figuras/eren.png", "equipo/emblemas/eren.png", "equipo/fondos/eren.jpg",
    "equipo/tex/muro.png",
]  # fmt: skip


@pytest.fixture
def con_assets(tmp_path: Path) -> temas.AssetsTema:
    for relativa in ASSETS_COMPLETOS:
        archivo = tmp_path / relativa
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_bytes(b"x")
    return temas.AssetsTema(tmp_path)


@pytest.fixture
def sin_assets(tmp_path: Path) -> temas.AssetsTema:
    return temas.AssetsTema(tmp_path / "no-existe")


def test_cuatro_temas_con_el_set_completo_de_tokens() -> None:
    assert set(temas.PALETAS) == {"mugiwara", "luffy_g5", "esmeralda", "eren"}
    assert set(temas.ETIQUETAS) == set(temas.PALETAS)
    for clave, paleta in temas.PALETAS.items():
        assert set(paleta) == set(TOKENS), clave


def test_paletas_identicas_a_jaime() -> None:
    """Copiadas tal cual: el acento de cada tema es el de Jaime."""
    assert temas.PALETAS["mugiwara"]["accent"] == "#F5C542"
    assert temas.PALETAS["luffy_g5"]["accent"] == "#F5F0E6"
    assert temas.PALETAS["esmeralda"]["accent"] == "#10B981"
    assert temas.PALETAS["eren"]["accent"] == "#4FF0B0"


def test_resolver_cae_al_tema_por_defecto() -> None:
    assert temas.resolver("esmeralda") == "esmeralda"
    assert temas.resolver("tema_borrado") == temas.TEMA_POR_DEFECTO
    assert temas.resolver(None) == "eren"


@pytest.mark.parametrize("clave", ["mugiwara", "luffy_g5", "esmeralda", "eren"])
def test_sin_assets_queda_con_colores_planos(clave: str, sin_assets: temas.AssetsTema) -> None:
    css = temas.css_del_tema(clave, sin_assets)
    assert temas.PALETAS[clave]["accent"] in css
    assert "/temas/" not in css, "no debe referenciar imágenes que no existen"
    assert ".ao-card" in css


@pytest.mark.parametrize(
    ("clave", "esperado"),
    [
        ("mugiwara", ["/temas/op/figuras/mugiwara.png", "/temas/op/mugiwara/skull.png",
                      "/temas/op/mugiwara/bg.jpg", "Pirata One"]),
        ("luffy_g5", ["/temas/op/figuras/luffy_g5.png", "/temas/op/tex/haki1.png", "haki-nika"]),
        ("esmeralda", ["/temas/op/rogers/zoro.png", "/temas/op/tex/haki2.png", "haki-corte"]),
        ("eren", ["/temas/equipo/figuras/eren.png", "/temas/equipo/fondos/eren.jpg",
                  "eren-rayo", "eren-vapor", "Cinzel"]),
    ],
)  # fmt: skip
def test_con_assets_viste_al_personaje(
    clave: str, esperado: list[str], con_assets: temas.AssetsTema
) -> None:
    css = temas.css_del_tema(clave, con_assets)
    for fragmento in esperado:
        assert fragmento in css, f"{clave}: falta {fragmento}"
    assert "prefers-reduced-motion" in css


def test_mugiwara_no_despierta_haki(con_assets: temas.AssetsTema) -> None:
    assert "haki-rayo" not in temas.css_del_tema("mugiwara", con_assets)


def test_una_piel_rota_no_rompe_la_ui(
    con_assets: temas.AssetsTema, caplog: pytest.LogCaptureFixture
) -> None:
    incompleta = {"accent": "#FFFFFF"}  # faltan tokens: la piel falla por dentro
    with caplog.at_level(logging.WARNING):
        assert piel_op("esmeralda", incompleta, con_assets) == ""
        assert piel_eren("eren", incompleta, con_assets) == ""
    assert "No se pudo construir la piel" in caplog.text


def test_piel_de_tema_ajeno_es_vacia(con_assets: temas.AssetsTema) -> None:
    assert piel_op("eren", temas.PALETAS["eren"], con_assets) == ""


def test_rgb() -> None:
    assert rgb("#4FF0B0") == "79,240,176"


@pytest.mark.parametrize("clave", ["mugiwara", "luffy_g5", "esmeralda", "eren"])
def test_boton_principal_legible_con_y_sin_assets(
    clave: str, con_assets: temas.AssetsTema, sin_assets: temas.AssetsTema
) -> None:
    """Regresión 2026-11-25: en Gear 5 el texto blanco de Quasar desaparecía sobre el acento."""
    for assets in (con_assets, sin_assets):
        css = temas.css_del_tema(clave, assets)
        assert ".q-btn.ao-btn-primary" in css
        assert "\n.ao-btn-primary {" not in css, "sin .q-btn el .text-white de Quasar le gana"
