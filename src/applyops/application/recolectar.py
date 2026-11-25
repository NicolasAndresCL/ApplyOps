"""Caso de uso: recolectar ofertas de todas las fuentes, puntuarlas y guardarlas.

Degradación elegante: si una fuente falla (`FuenteNoDisponibleError`), se
registra en el resumen y el ciclo sigue con las demás. Cualquier otro error
es un bug y sube.

Un candado impide dos recolecciones simultáneas (el scheduler y un
`POST /recolecciones` manual), que duplicarían las llamadas a las fuentes sin
aportar nada.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime

from applyops.domain.errores import FuenteNoDisponibleError, RecoleccionEnCursoError
from applyops.domain.oferta import Oferta
from applyops.domain.perfil import PerfilBusqueda
from applyops.domain.puertos import FuenteOfertas, RepoOfertas
from applyops.domain.scoring import OfertaPuntuada, puntuar

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ResultadoFuente:
    """Lo que dejó una fuente en un ciclo. `error` no vacío = fuente degradada."""

    fuente: str
    encontradas: int
    nuevas: int
    error: str | None = None


@dataclass(frozen=True, slots=True)
class ResumenRecoleccion:
    """Resultado de un ciclo completo de recolección."""

    inicio: datetime
    fin: datetime
    resultados: tuple[ResultadoFuente, ...]

    @property
    def total_nuevas(self) -> int:
        return sum(r.nuevas for r in self.resultados)

    @property
    def fuentes_con_error(self) -> tuple[str, ...]:
        return tuple(r.fuente for r in self.resultados if r.error is not None)


class RecolectarOfertas:
    """Recorre las fuentes con las consultas del perfil y guarda lo encontrado ya puntuado."""

    def __init__(
        self,
        fuentes: Sequence[FuenteOfertas],
        repo: RepoOfertas,
        perfil: PerfilBusqueda,
        reloj: Callable[[], datetime],
    ) -> None:
        self._fuentes = tuple(fuentes)
        self._repo = repo
        self._perfil = perfil
        self._reloj = reloj
        self._candado = threading.Lock()

    def ejecutar(self) -> ResumenRecoleccion:
        """Corre un ciclo. Lanza `RecoleccionEnCursoError` si ya hay otro corriendo."""
        if not self._candado.acquire(blocking=False):
            raise RecoleccionEnCursoError
        try:
            inicio = self._reloj()
            resultados = tuple(self._recolectar_fuente(f) for f in self._fuentes)
            resumen = ResumenRecoleccion(inicio=inicio, fin=self._reloj(), resultados=resultados)
        finally:
            self._candado.release()
        logger.info(
            "Recolección terminada",
            extra={
                "nuevas": resumen.total_nuevas,
                "fuentes_con_error": list(resumen.fuentes_con_error),
                "segundos": round((resumen.fin - resumen.inicio).total_seconds(), 2),
            },
        )
        return resumen

    def _recolectar_fuente(self, fuente: FuenteOfertas) -> ResultadoFuente:
        try:
            ofertas = self._buscar_todas(fuente)
        except FuenteNoDisponibleError as error:
            logger.warning(
                "Fuente degradada: se omite en este ciclo",
                extra={"fuente": fuente.nombre, "motivo": error.motivo},
            )
            return ResultadoFuente(fuente.nombre, encontradas=0, nuevas=0, error=error.motivo)
        ahora = self._reloj()
        puntuadas = [OfertaPuntuada(o, puntuar(o, self._perfil), ahora) for o in ofertas]
        nuevas = self._repo.guardar(puntuadas)
        return ResultadoFuente(fuente.nombre, encontradas=len(ofertas), nuevas=nuevas)

    def _buscar_todas(self, fuente: FuenteOfertas) -> list[Oferta]:
        # Varias consultas devuelven la misma oferta («python» y «backend»):
        # se deduplica por clave antes de puntuar y guardar.
        por_clave: dict[str, Oferta] = {}
        for consulta in self._perfil.consultas:
            for oferta in fuente.buscar(consulta):
                por_clave.setdefault(oferta.clave, oferta)
        return list(por_clave.values())
