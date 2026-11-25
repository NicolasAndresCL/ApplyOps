"""Caso de uso: consultar la bandeja de ofertas priorizada.

Hoy es una capa delgada sobre el repositorio; existe para que la API dependa
de un caso de uso y no de la persistencia, y para que reglas futuras (ocultar
ofertas ya postuladas, marcar las vencidas) tengan dónde vivir.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

from applyops.domain.puertos import FiltroOfertas, RepoOfertas
from applyops.domain.scoring import OfertaPuntuada


class ConsultarOfertas:
    """Lectura de ofertas puntuadas."""

    def __init__(self, repo: RepoOfertas) -> None:
        self._repo = repo

    def listar(self, filtro: FiltroOfertas) -> list[OfertaPuntuada]:
        return self._repo.listar(filtro)

    def obtener(self, clave: str) -> OfertaPuntuada:
        return self._repo.obtener(clave)
