"""Caso de uso de recolección: degradación por fuente, deduplicación e idempotencia.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

import threading

import pytest

from applyops.application.recolectar import RecolectarOfertas
from applyops.domain.errores import FuenteNoDisponibleError, RecoleccionEnCursoError
from applyops.domain.puertos import FuenteOfertas, ResultadoBusqueda
from applyops.domain.scoring import OfertaPuntuada, puntuar
from tests.fakes import AHORA, FuenteCaida, FuenteFalsa, RepoEnMemoria, un_perfil, una_oferta


def _caso(fuentes: list[FuenteOfertas], repo: RepoEnMemoria) -> RecolectarOfertas:
    perfil = un_perfil(consultas=("python", "backend"))
    return RecolectarOfertas(fuentes, repo, perfil, reloj=lambda: AHORA)


def test_guarda_ofertas_puntuadas() -> None:
    repo = RepoEnMemoria()
    fuente = FuenteFalsa("falsa", {"python": [una_oferta()]})
    resumen = _caso([fuente], repo).ejecutar()

    assert resumen.total_nuevas == 1
    assert repo.filas["falsa:1"].puntaje.total == 95
    assert fuente.consultas == ["python", "backend"]


def test_deduplica_la_misma_oferta_entre_consultas() -> None:
    repo = RepoEnMemoria()
    misma = una_oferta()
    fuente = FuenteFalsa("falsa", {"python": [misma], "backend": [misma]})
    resultado = _caso([fuente], repo).ejecutar().resultados[0]
    assert (resultado.encontradas, resultado.nuevas) == (1, 1)


def test_segunda_corrida_no_duplica() -> None:
    repo = RepoEnMemoria()
    caso = _caso([FuenteFalsa("falsa", {"python": [una_oferta()]})], repo)
    caso.ejecutar()
    assert caso.ejecutar().total_nuevas == 0
    assert len(repo.filas) == 1


def test_fuente_caida_degrada_sin_cortar_las_demas() -> None:
    repo = RepoEnMemoria()
    sana = FuenteFalsa("sana", {"python": [una_oferta(fuente="sana")]})
    resumen = _caso([FuenteCaida(), sana], repo).ejecutar()

    assert resumen.fuentes_con_error == ("caida",)
    assert (
        resumen.resultados[0].error
        == "«python»: HTTP 503 tras 3 intentos; «backend»: HTTP 503 tras 3 intentos"
    )
    assert resumen.total_nuevas == 1


def test_no_permite_dos_recolecciones_a_la_vez() -> None:
    dentro = threading.Event()
    soltar = threading.Event()

    class FuenteLenta:
        nombre = "lenta"

        def buscar(self, consulta: str) -> ResultadoBusqueda:
            dentro.set()
            soltar.wait(timeout=5)
            return ResultadoBusqueda([])

    caso = _caso([FuenteLenta()], RepoEnMemoria())
    hilo = threading.Thread(target=caso.ejecutar)
    hilo.start()
    try:
        assert dentro.wait(timeout=5)
        with pytest.raises(RecoleccionEnCursoError):
            caso.ejecutar()
    finally:
        soltar.set()
        hilo.join(timeout=5)
    # Liberado el candado, se puede volver a correr.
    assert caso.ejecutar().total_nuevas == 0


class FuenteIntermitente:
    """Responde «python» pero falla en «backend»: una respuesta parcial."""

    nombre = "intermitente"

    def buscar(self, consulta: str) -> ResultadoBusqueda:
        if consulta == "backend":
            raise FuenteNoDisponibleError(self.nombre, "timeout tras 3 intentos")
        return ResultadoBusqueda([una_oferta(fuente=self.nombre)])


def test_consulta_caida_no_descarta_lo_que_trajeron_las_demas() -> None:
    """Regresión (revisión de Sourcery, 2026-11-25): antes se perdía toda la fuente."""
    repo = RepoEnMemoria()
    resultado = _caso([FuenteIntermitente()], repo).ejecutar().resultados[0]
    assert (resultado.encontradas, resultado.nuevas) == (1, 1)
    assert resultado.error == "«backend»: timeout tras 3 intentos"
    assert "intermitente:1" in repo.filas


def test_vence_lo_que_la_fuente_ya_no_publica_y_revive_si_vuelve() -> None:
    repo = RepoEnMemoria()
    ofertas = {"python": [una_oferta(id_externo="1"), una_oferta(id_externo="2")]}
    fuente = FuenteFalsa("falsa", ofertas)
    caso = _caso([fuente], repo)
    caso.ejecutar()

    ofertas["python"] = [una_oferta(id_externo="1")]  # la 2 se cerró
    assert caso.ejecutar().resultados[0].vencidas == 1
    assert repo.filas["falsa:2"].vencida_en == AHORA
    assert repo.filas["falsa:1"].vencida_en is None

    ofertas["python"] = [una_oferta(id_externo="1"), una_oferta(id_externo="2")]  # reapareció
    assert caso.ejecutar().resultados[0].vencidas == 0
    assert repo.filas["falsa:2"].vencida_en is None


def test_respuesta_parcial_no_vence_nada() -> None:
    """Si una consulta falló, que una oferta falte no prueba que se cerró."""
    repo = RepoEnMemoria()
    repo.guardar([OfertaPuntuada(una_oferta(fuente="intermitente", id_externo="vieja"),
                                 puntuar(una_oferta(), un_perfil()), AHORA)])  # fmt: skip
    resultado = _caso([FuenteIntermitente()], repo).ejecutar().resultados[0]
    assert resultado.vencidas == 0
    assert repo.filas["intermitente:vieja"].vencida_en is None


def test_las_manuales_no_vencen() -> None:
    repo = RepoEnMemoria()
    manual = una_oferta(fuente="manual", id_externo="abc")
    repo.guardar([OfertaPuntuada(manual, puntuar(manual, un_perfil()), AHORA)])
    _caso([FuenteFalsa("falsa", {"python": []})], repo).ejecutar()
    assert repo.filas["manual:abc"].vencida_en is None


def test_resultado_incompleto_no_vence_ofertas_vivas() -> None:
    """Regresión (Sourcery, PR #5): con corte por tope de páginas se vencían ofertas abiertas."""
    repo = RepoEnMemoria()
    ofertas = {"python": [una_oferta(id_externo="1"), una_oferta(id_externo="2")]}
    fuente = FuenteFalsa("falsa", ofertas)
    caso = _caso([fuente], repo)
    caso.ejecutar()

    ofertas["python"] = [una_oferta(id_externo="1")]  # la 2 quedó más allá del tope
    fuente.completa = False
    assert caso.ejecutar().resultados[0].vencidas == 0
    assert repo.filas["falsa:2"].vencida_en is None
