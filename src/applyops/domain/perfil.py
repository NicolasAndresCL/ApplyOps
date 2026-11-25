"""Criterios de búsqueda del candidato: qué ofertas valen la pena y cuánto.

Es el contrato entre el archivo `perfil/busqueda.yaml` (lo carga un adaptador)
y el scoring. Todo número que influye en el puntaje vive acá, con nombre, en
vez de estar repartido como constante mágica dentro de las reglas.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from applyops.domain.errores import PerfilInvalidoError
from applyops.domain.oferta import Modalidad, Seniority

PUNTAJE_MAXIMO = 100


@dataclass(frozen=True, slots=True)
class Skill:
    """Una tecnología del perfil. `peso` (1–3) indica cuánto suma si la oferta la pide."""

    nombre: str
    peso: int = 1
    sinonimos: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 1 <= self.peso <= 3:
            raise PerfilInvalidoError(f"Peso de {self.nombre!r} fuera de 1–3: {self.peso}")

    @property
    def terminos(self) -> tuple[str, ...]:
        """Todas las formas en que una oferta puede mencionar esta skill."""
        return (self.nombre, *self.sinonimos)


@dataclass(frozen=True, slots=True)
class PesosScoring:
    """Puntos máximos de cada componente. Deben sumar 100 para que el total sea un porcentaje."""

    stack: int = 50
    modalidad: int = 20
    sueldo: int = 15
    seniority: int = 10
    idioma: int = 5

    def __post_init__(self) -> None:
        suma = self.stack + self.modalidad + self.sueldo + self.seniority + self.idioma
        if suma != PUNTAJE_MAXIMO:
            raise PerfilInvalidoError(f"Los pesos deben sumar {PUNTAJE_MAXIMO}, suman {suma}")


@dataclass(frozen=True, slots=True)
class PerfilBusqueda:
    """Todo lo que el scoring necesita saber del candidato.

    - `saturacion_stack`: suma de pesos de skills mencionadas que ya otorga el 100 %
      del componente stack. Sin tope, una oferta que lista 30 tecnologías ganaría
      siempre a una precisa que pide exactamente las 5 tuyas.
    - `factor_modalidad` / `factor_seniority`: fracción (0–1) del componente que
      otorga cada valor. Lo que no esté en el mapa vale 0.
    - `paises_presenciales`: donde se acepta trabajar con presencia física o remoto
      restringido por país. Fuera de ellos, una oferta no remota se descarta.
    - `palabras_descarte`: si aparecen en el título, la oferta se descarta
      (p. ej. «ventas», «práctica»).
    """

    consultas: tuple[str, ...]
    skills: tuple[Skill, ...]
    saturacion_stack: int = 10
    sueldo_minimo_usd: int | None = None
    factor_modalidad: Mapping[Modalidad, float] = field(default_factory=dict)
    paises_presenciales: tuple[str, ...] = ()
    factor_seniority: Mapping[Seniority, float] = field(default_factory=dict)
    idiomas: tuple[str, ...] = ("es",)
    palabras_descarte: tuple[str, ...] = ()
    pesos: PesosScoring = field(default_factory=PesosScoring)

    def __post_init__(self) -> None:
        if not self.consultas:
            raise PerfilInvalidoError("El perfil necesita al menos una consulta de búsqueda")
        if not self.skills:
            raise PerfilInvalidoError("El perfil necesita al menos una skill")
        if self.saturacion_stack < 1:
            raise PerfilInvalidoError("saturacion_stack debe ser ≥ 1")
        for nombre, mapa in (
            ("factor_modalidad", self.factor_modalidad),
            ("factor_seniority", self.factor_seniority),
        ):
            for clave, factor in mapa.items():
                if not 0 <= factor <= 1:
                    raise PerfilInvalidoError(f"{nombre}[{clave}] fuera de 0–1: {factor}")
