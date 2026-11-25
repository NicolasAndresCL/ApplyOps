"""Invariantes de las entidades del dominio: datos rotos fallan al construirse.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

import pytest

from applyops.domain.errores import OfertaInvalidaError, PerfilInvalidoError
from applyops.domain.oferta import Modalidad
from applyops.domain.perfil import PesosScoring, Skill
from tests.fakes import un_perfil, una_oferta


class TestOferta:
    def test_clave_natural(self) -> None:
        assert una_oferta(fuente="getonboard", id_externo="abc").clave == "getonboard:abc"

    @pytest.mark.parametrize("campo", ["fuente", "id_externo", "titulo", "url"])
    def test_campos_obligatorios(self, campo: str) -> None:
        with pytest.raises(OfertaInvalidaError, match=campo):
            una_oferta(**{campo: "  "})

    def test_sueldo_invertido(self) -> None:
        with pytest.raises(OfertaInvalidaError, match="invertido"):
            una_oferta(sueldo_min_usd=3000, sueldo_max_usd=1000)

    def test_sueldo_negativo(self) -> None:
        with pytest.raises(OfertaInvalidaError, match="negativo"):
            una_oferta(sueldo_min_usd=-1)


class TestPerfil:
    def test_pesos_deben_sumar_100(self) -> None:
        with pytest.raises(PerfilInvalidoError, match="suman 90"):
            PesosScoring(stack=40)

    def test_pesos_negativos_aunque_sumen_100(self) -> None:
        """Regresión (Sourcery, 2026-11-25): solo se validaba la suma."""
        with pytest.raises(PerfilInvalidoError, match="negativos: idioma"):
            PesosScoring(stack=60, idioma=-5)

    def test_peso_de_skill_fuera_de_rango(self) -> None:
        with pytest.raises(PerfilInvalidoError, match="1–3"):
            Skill("Python", peso=5)

    def test_skill_expone_sus_terminos(self) -> None:
        assert Skill("PostgreSQL", 2, ("postgres",)).terminos == ("PostgreSQL", "postgres")

    @pytest.mark.parametrize(
        ("cambios", "mensaje"),
        [
            ({"consultas": ()}, "consulta"),
            ({"skills": ()}, "skill"),
            ({"saturacion_stack": 0}, "saturacion_stack"),
            ({"factor_modalidad": {Modalidad.REMOTO: 1.5}}, "factor_modalidad"),
        ],
    )
    def test_perfil_invalido(self, cambios: dict[str, object], mensaje: str) -> None:
        with pytest.raises(PerfilInvalidoError, match=mensaje):
            un_perfil(**cambios)
