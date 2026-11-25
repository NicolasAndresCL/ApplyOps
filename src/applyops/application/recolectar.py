"""Caso de uso: recolectar ofertas de todas las fuentes, puntuarlas y guardarlas.

Degradación elegante: si una consulta de una fuente falla
(`FuenteNoDisponibleError`), se registra en el resumen, se guardan igual las
ofertas que trajeron las demás consultas de esa fuente y el ciclo sigue con las
otras fuentes. Cualquier otro error es un bug y sube.

Vencimiento: solo cuando una fuente respondió COMPLETA (todas sus consultas sin
error), sus ofertas guardadas que ya no vinieron se marcan vencidas. Con una
respuesta parcial, que una oferta falte no prueba que se cerró.

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
    vencidas: int = 0


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
        ofertas, errores = self._buscar_todas(fuente)
        error = "; ".join(errores) if errores else None
        if errores:
            logger.warning(
                "Fuente degradada: se guarda lo que respondió",
                extra={"fuente": fuente.nombre, "motivo": error, "ofertas": len(ofertas)},
            )
        ahora = self._reloj()
        puntuadas = [OfertaPuntuada(o, puntuar(o, self._perfil), ahora) for o in ofertas]
        nuevas = self._repo.guardar(puntuadas)
        vencidas = 0
        if not errores:
            vencidas = self._repo.marcar_vencidas(fuente.nombre, [o.clave for o in ofertas], ahora)
        return ResultadoFuente(
            fuente.nombre, encontradas=len(ofertas), nuevas=nuevas, error=error, vencidas=vencidas
        )

    def _buscar_todas(self, fuente: FuenteOfertas) -> tuple[list[Oferta], list[str]]:
        """Ofertas de todas las consultas (deduplicadas) y los motivos de las que fallaron.

        Varias consultas devuelven la misma oferta («python» y «backend»): se
        deduplica por clave. Una consulta caída no descarta lo que trajeron las demás.
        """
        por_clave: dict[str, Oferta] = {}
        errores: list[str] = []
        for consulta in self._perfil.consultas:
            try:
                resultado = fuente.buscar(consulta)
            except FuenteNoDisponibleError as error:
                errores.append(f"«{consulta}»: {error.motivo}")
                continue
            for oferta in resultado:
                por_clave.setdefault(oferta.clave, oferta)
        return list(por_clave.values()), errores
