"""Puertos del dominio: lo que el núcleo necesita del mundo exterior.

Los casos de uso dependen de estos `Protocol`, nunca de httpx ni de
SQLAlchemy. Cada fuente de ofertas y cada base de datos es un adaptador que
los implementa; en los tests se reemplazan por fakes en memoria.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from applyops.domain.oferta import Oferta
from applyops.domain.scoring import OfertaPuntuada


class FuenteOfertas(Protocol):
    """Una fuente de ofertas con API o feed público (ver ADR 0001)."""

    @property
    def nombre(self) -> str: ...

    def buscar(self, consulta: str) -> list[Oferta]:
        """Ofertas que calzan con la consulta.

        Lanza `FuenteNoDisponibleError` si la fuente no responde bien tras los
        reintentos; nunca devuelve una lista vacía para disimular un fallo.
        """
        ...


@dataclass(frozen=True, slots=True)
class FiltroOfertas:
    """Criterios de listado. `limite` acota la respuesta para no traer la tabla entera."""

    min_puntaje: int = 0
    incluir_descartadas: bool = False
    incluir_vencidas: bool = False
    limite: int = 50


class RepoOfertas(Protocol):
    """Persistencia de ofertas puntuadas."""

    def guardar(self, puntuadas: Sequence[OfertaPuntuada]) -> int:
        """Inserta las nuevas y actualiza las existentes (por `clave`).

        Lo guardado deja de estar vencido (reapareció en su fuente).

        Devuelve cuántas eran nuevas. Idempotente: guardar dos veces lo mismo
        no duplica ni cambia `vista_en`.
        """
        ...

    def marcar_vencidas(self, fuente: str, vigentes: Collection[str], momento: datetime) -> int:
        """Marca vencidas las ofertas de `fuente` cuya clave no está en `vigentes`.

        Solo se llama tras una recolección COMPLETA de esa fuente (si una consulta
        falló, faltar no prueba que la oferta se cerró). Devuelve cuántas venció.
        """
        ...

    def listar(self, filtro: FiltroOfertas) -> list[OfertaPuntuada]:
        """Ofertas ordenadas por puntaje descendente y, a igual puntaje, las más nuevas primero."""
        ...

    def obtener(self, clave: str) -> OfertaPuntuada:
        """La oferta con esa clave. Lanza `OfertaNoEncontradaError` si no existe."""
        ...

    def disponible(self) -> bool:
        """¿La base de datos responde? Lo usa `/ready`."""
        ...
