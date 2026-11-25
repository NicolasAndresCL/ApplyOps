"""Caso de uso de recolección: degradación por fuente, deduplicación e idempotencia.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

import threading

import pytest

from applyops.application.recolectar import RecolectarOfertas
from applyops.domain.errores import RecoleccionEnCursoError
from applyops.domain.oferta import Oferta
from applyops.domain.puertos import FuenteOfertas
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
    assert resumen.resultados[0].error == "HTTP 503 tras 3 intentos"
    assert resumen.total_nuevas == 1


def test_no_permite_dos_recolecciones_a_la_vez() -> None:
    dentro = threading.Event()
    soltar = threading.Event()

    class FuenteLenta:
        nombre = "lenta"

        def buscar(self, consulta: str) -> list[Oferta]:
            dentro.set()
            soltar.wait(timeout=5)
            return []

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
