"""Fakes de los puertos y fábricas de datos para los tests.

Implementan el contrato del puerto (no mockean la implementación): si un caso
de uso funciona con estos fakes, funciona con cualquier adaptador que cumpla
el mismo contrato.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

from applyops.domain.errores import FuenteNoDisponibleError, OfertaNoEncontradaError
from applyops.domain.oferta import Modalidad, Oferta, Seniority
from applyops.domain.perfil import PerfilBusqueda, Skill
from applyops.domain.puertos import FiltroOfertas
from applyops.domain.scoring import OfertaPuntuada

AHORA = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)


def una_oferta(**cambios: Any) -> Oferta:
    base = Oferta(
        fuente="falsa",
        id_externo="1",
        titulo="Backend Developer Python",
        empresa="ACME",
        url="https://ejemplo.cl/ofertas/1",
        descripcion="Buscamos experiencia con Python, FastAPI y PostgreSQL en Docker.",
        modalidad=Modalidad.REMOTO,
        paises=(),
        sueldo_min_usd=2000,
        sueldo_max_usd=3000,
        seniority=Seniority.SEMI_SENIOR,
        idioma="es",
        publicada_en=AHORA,
    )
    return replace(base, **cambios)


def un_perfil(**cambios: Any) -> PerfilBusqueda:
    base = PerfilBusqueda(
        consultas=("python",),
        skills=(
            Skill("Python", 3),
            Skill("FastAPI", 2),
            Skill("PostgreSQL", 2, ("postgres",)),
            Skill("Docker", 2),
            Skill("Kubernetes", 2, ("k8s",)),
            Skill("CI/CD", 1, ("github actions",)),
        ),
        saturacion_stack=10,
        sueldo_minimo_usd=1500,
        factor_modalidad={
            Modalidad.REMOTO: 1.0,
            Modalidad.REMOTO_LOCAL: 1.0,
            Modalidad.HIBRIDO: 0.6,
            Modalidad.PRESENCIAL: 0.2,
        },
        paises_presenciales=("Chile",),
        factor_seniority={
            Seniority.JUNIOR: 0.8,
            Seniority.SEMI_SENIOR: 1.0,
            Seniority.SENIOR: 0.6,
        },
        idiomas=("es", "en"),
        palabras_descarte=("ventas", "práctica"),
    )
    return replace(base, **cambios)


class FuenteFalsa:
    """Devuelve ofertas fijas por consulta y registra qué se le pidió."""

    def __init__(self, nombre: str, por_consulta: dict[str, list[Oferta]]) -> None:
        self.nombre = nombre
        self._por_consulta = por_consulta
        self.consultas: list[str] = []

    def buscar(self, consulta: str) -> list[Oferta]:
        self.consultas.append(consulta)
        return list(self._por_consulta.get(consulta, []))


class FuenteCaida:
    """Siempre falla como falla una fuente real tras agotar reintentos."""

    def __init__(self, nombre: str = "caida") -> None:
        self.nombre = nombre

    def buscar(self, consulta: str) -> list[Oferta]:
        raise FuenteNoDisponibleError(self.nombre, "HTTP 503 tras 3 intentos")


class RepoEnMemoria:
    """Repositorio con la misma semántica que el de SQLAlchemy (idempotente por clave)."""

    def __init__(self, disponible: bool = True) -> None:
        self.filas: dict[str, OfertaPuntuada] = {}
        self._disponible = disponible

    def guardar(self, puntuadas: Sequence[OfertaPuntuada]) -> int:
        nuevas = 0
        for p in puntuadas:
            previa = self.filas.get(p.oferta.clave)
            if previa is None:
                nuevas += 1
                self.filas[p.oferta.clave] = p
            else:
                self.filas[p.oferta.clave] = replace(p, vista_en=previa.vista_en)
        return nuevas

    def listar(self, filtro: FiltroOfertas) -> list[OfertaPuntuada]:
        filas = [
            p
            for p in self.filas.values()
            if p.puntaje.total >= filtro.min_puntaje
            and (filtro.incluir_descartadas or not p.puntaje.descartada)
        ]
        filas.sort(key=lambda p: (-p.puntaje.total, p.oferta.clave))
        return filas[: filtro.limite]

    def obtener(self, clave: str) -> OfertaPuntuada:
        try:
            return self.filas[clave]
        except KeyError:
            raise OfertaNoEncontradaError(clave) from None

    def disponible(self) -> bool:
        return self._disponible
