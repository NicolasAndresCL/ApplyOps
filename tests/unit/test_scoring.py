"""Reglas del scoring: cada componente, los descartes y el matching de términos.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

import pytest

from applyops.domain.oferta import Modalidad, Seniority
from applyops.domain.scoring import Puntaje, menciona, normalizar, puntuar
from tests.fakes import un_perfil, una_oferta


def _componente(puntaje: Puntaje, nombre: str) -> tuple[float, str]:
    c = next(c for c in puntaje.componentes if c.nombre == nombre)
    return c.puntos, c.detalle


class TestMatching:
    def test_normaliza_tildes_y_mayusculas(self) -> None:
        assert normalizar("Automatización ÁGIL") == "automatizacion agil"

    @pytest.mark.parametrize(
        ("texto", "termino", "esperado"),
        [
            ("sabemos python y sql", "Python", True),
            ("trabajamos con pythonic code", "python", False),  # palabra completa
            ("pipelines ci/cd en github", "CI/CD", True),  # término con símbolo
            ("experiencia en c# y .net", "c#", True),
            ("usamos postgresql 16", "postgres", False),  # sinónimo no es substring
            ("manejo de k8s", "k8s", True),
        ],
    )
    def test_menciona_como_palabra_completa(self, texto: str, termino: str, esperado: bool) -> None:
        assert menciona(normalizar(texto), termino) is esperado


class TestStack:
    def test_suma_pesos_de_skills_mencionadas(self) -> None:
        # Python 3 + FastAPI 2 + PostgreSQL 2 + Docker 2 = 9 de saturación 10 → 45 de 50.
        puntos, detalle = _componente(puntuar(una_oferta(), un_perfil()), "stack")
        assert puntos == pytest.approx(45)
        assert detalle == "Pide: Python, FastAPI, PostgreSQL, Docker"

    def test_satura_en_el_maximo(self) -> None:
        oferta = una_oferta(descripcion="Python FastAPI PostgreSQL Docker Kubernetes CI/CD")
        puntos, _ = _componente(puntuar(oferta, un_perfil()), "stack")
        assert puntos == 50

    def test_sinonimo_cuenta_como_la_skill(self) -> None:
        oferta = una_oferta(titulo="Dev", descripcion="Clusters k8s")
        _, detalle = _componente(puntuar(oferta, un_perfil()), "stack")
        assert detalle == "Pide: Kubernetes"

    def test_sin_skills_vale_cero(self) -> None:
        oferta = una_oferta(titulo="Diseñador", descripcion="Figma y Photoshop")
        puntos, detalle = _componente(puntuar(oferta, un_perfil()), "stack")
        assert puntos == 0
        assert "ninguna" in detalle


class TestModalidad:
    @pytest.mark.parametrize(
        ("modalidad", "esperado"),
        [
            (Modalidad.REMOTO, 20),
            (Modalidad.HIBRIDO, 12),
            (Modalidad.PRESENCIAL, 4),
            (Modalidad.DESCONOCIDA, 10),
        ],
    )
    def test_factor_por_modalidad(self, modalidad: Modalidad, esperado: float) -> None:
        oferta = una_oferta(modalidad=modalidad, paises=("Chile",))
        puntos, _ = _componente(puntuar(oferta, un_perfil()), "modalidad")
        assert puntos == pytest.approx(esperado)

    def test_hibrido_fuera_de_paises_aceptados_se_descarta(self) -> None:
        oferta = una_oferta(modalidad=Modalidad.HIBRIDO, paises=("Argentina",))
        puntaje = puntuar(oferta, un_perfil())
        assert puntaje.descartada
        assert puntaje.total == 0
        assert "Argentina" in (puntaje.descarte or "")
        assert len(puntaje.componentes) == 5, "el descarte conserva el desglose"

    def test_remoto_no_se_descarta_por_pais(self) -> None:
        oferta = una_oferta(modalidad=Modalidad.REMOTO, paises=("Argentina",))
        assert not puntuar(oferta, un_perfil()).descartada

    def test_paises_se_comparan_sin_tildes(self) -> None:
        perfil = un_perfil(paises_presenciales=("Perú",))
        oferta = una_oferta(modalidad=Modalidad.PRESENCIAL, paises=("peru",))
        assert not puntuar(oferta, perfil).descartada


class TestSueldo:
    @pytest.mark.parametrize(
        ("minimo", "maximo", "esperado", "texto"),
        [
            (2000, 3000, 15, "sobre tu mínimo"),
            (500, 1000, 0, "bajo tu mínimo"),
            (1000, 2000, 7.5, "cruza tu mínimo"),  # la mitad del rango supera 1.500
            (None, 2500, 15, "sobre tu mínimo"),  # solo máximo: piso = tope
            (None, None, 7.5, "no publicado"),
        ],
    )
    def test_rango_contra_minimo(
        self, minimo: int | None, maximo: int | None, esperado: float, texto: str
    ) -> None:
        oferta = una_oferta(sueldo_min_usd=minimo, sueldo_max_usd=maximo)
        puntos, detalle = _componente(puntuar(oferta, un_perfil()), "sueldo")
        assert puntos == pytest.approx(esperado)
        assert texto in detalle

    def test_sin_minimo_en_perfil_da_el_maximo(self) -> None:
        oferta = una_oferta(sueldo_min_usd=100, sueldo_max_usd=200)
        puntos, _ = _componente(puntuar(oferta, un_perfil(sueldo_minimo_usd=None)), "sueldo")
        assert puntos == 15


class TestSeniorityEIdioma:
    @pytest.mark.parametrize(
        ("seniority", "esperado"),
        [(Seniority.SEMI_SENIOR, 10), (Seniority.SENIOR, 6), (Seniority.EXPERTO, 0), (None, 5)],
    )
    def test_factor_de_seniority(self, seniority: Seniority | None, esperado: float) -> None:
        puntos, _ = _componente(puntuar(una_oferta(seniority=seniority), un_perfil()), "seniority")
        assert puntos == pytest.approx(esperado)

    @pytest.mark.parametrize(("idioma", "esperado"), [("en", 5), (None, 5), ("pt", 0)])
    def test_idioma(self, idioma: str | None, esperado: float) -> None:
        puntos, _ = _componente(puntuar(una_oferta(idioma=idioma), un_perfil()), "idioma")
        assert puntos == esperado


class TestTotal:
    def test_suma_componentes_y_redondea(self) -> None:
        # stack 45 + modalidad 20 + sueldo 15 + seniority 10 + idioma 5 = 95
        assert puntuar(una_oferta(), un_perfil()).total == 95

    def test_palabra_de_descarte_en_el_titulo(self) -> None:
        oferta = una_oferta(titulo="Práctica profesional Python")
        puntaje = puntuar(oferta, un_perfil())
        assert puntaje.total == 0
        assert puntaje.descarte == "El título contiene «práctica»"

    def test_palabra_de_descarte_solo_en_descripcion_no_descarta(self) -> None:
        oferta = una_oferta(descripcion="Apoyarás al equipo de ventas con Python")
        assert not puntuar(oferta, un_perfil()).descartada

    def test_es_determinista(self) -> None:
        assert puntuar(una_oferta(), un_perfil()) == puntuar(una_oferta(), un_perfil())
