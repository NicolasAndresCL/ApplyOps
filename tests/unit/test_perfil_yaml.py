"""Carga y validación de perfil/busqueda.yaml.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

import pytest

from applyops.adapters.outbound.perfil_yaml import cargar_perfil
from applyops.domain.errores import PerfilInvalidoError
from applyops.domain.oferta import Modalidad, Seniority

EJEMPLO = Path(__file__).parents[2] / "perfil" / "busqueda.example.yaml"


def test_el_ejemplo_versionado_es_valido() -> None:
    perfil = cargar_perfil(EJEMPLO)
    assert "python" in perfil.consultas
    assert perfil.skills[0].nombre == "Python"
    assert perfil.factor_modalidad[Modalidad.REMOTO] == 1.0
    assert perfil.factor_seniority[Seniority.SEMI_SENIOR] == 1.0
    assert perfil.pesos.stack == 50


def test_sin_perfil_real_usa_el_ejemplo_y_avisa(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    shutil.copy(EJEMPLO, tmp_path / "busqueda.example.yaml")
    with caplog.at_level(logging.WARNING):
        perfil = cargar_perfil(tmp_path / "busqueda.yaml")
    assert perfil.consultas
    assert "se usa el ejemplo" in caplog.text


def test_sin_ningun_archivo_falla(tmp_path: Path) -> None:
    with pytest.raises(PerfilInvalidoError, match="No existe"):
        cargar_perfil(tmp_path / "busqueda.yaml")


@pytest.mark.parametrize(
    ("contenido", "mensaje"),
    [
        ("consultas: [python]\nskills: [{nombre: Python}]\nclave_mal_escrita: 1\n", "clave_mal"),
        (
            "consultas: [python]\nskills: [{nombre: Python}]\nmodalidad: {teletrabajo: 1}\n",
            "modalidad",
        ),
        ("consultas: [python]\nskills: [{nombre: Python, peso: 9}]\n", "peso"),
        ("consultas: []\nskills: [{nombre: Python}]\n", "consultas"),
        ("consultas: [python\n", "YAML mal formado"),
    ],
)
def test_perfil_invalido_da_mensaje_claro(tmp_path: Path, contenido: str, mensaje: str) -> None:
    ruta = tmp_path / "busqueda.yaml"
    ruta.write_text(contenido, encoding="utf-8")
    with pytest.raises(PerfilInvalidoError, match=mensaje):
        cargar_perfil(ruta)


def test_pesos_que_no_suman_100(tmp_path: Path) -> None:
    ruta = tmp_path / "busqueda.yaml"
    ruta.write_text(
        "consultas: [python]\nskills: [{nombre: Python}]\npesos: {stack: 10}\n", encoding="utf-8"
    )
    with pytest.raises(PerfilInvalidoError, match="sumar 100"):
        cargar_perfil(ruta)
