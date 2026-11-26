"""Repositorio SQLAlchemy contra una base real (SQLite o PostgreSQL según el entorno).

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

import time
from dataclasses import replace
from datetime import timedelta

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from applyops.adapters.outbound.modelos_sqlalchemy import Base
from applyops.adapters.outbound.repo_sqlalchemy import RepoOfertasSqlAlchemy
from applyops.domain.errores import OfertaNoEncontradaError
from applyops.domain.oferta import Modalidad, Seniority
from applyops.domain.puertos import IDIOMA_NO_INDICA, FiltroOfertas
from applyops.domain.scoring import OfertaPuntuada, puntuar
from applyops.infra.db import crear_motor
from tests.fakes import AHORA, un_perfil, una_oferta

pytestmark = pytest.mark.integracion


def _puntuada(**cambios: object) -> OfertaPuntuada:
    oferta = una_oferta(**cambios)
    return OfertaPuntuada(oferta, puntuar(oferta, un_perfil()), AHORA)


@pytest.fixture
def repo(sesiones: sessionmaker[Session]) -> RepoOfertasSqlAlchemy:
    return RepoOfertasSqlAlchemy(sesiones, reloj=lambda: AHORA)


def test_las_migraciones_coinciden_con_los_modelos(motor: Engine) -> None:
    """Si alguien cambia un modelo sin migración, este test lo detecta."""
    with motor.connect() as conexion:
        diferencias = compare_metadata(MigrationContext.configure(conexion), Base.metadata)
    assert diferencias == []


def test_ida_y_vuelta_conserva_todos_los_campos(repo: RepoOfertasSqlAlchemy) -> None:
    original = _puntuada(paises=("Chile", "Perú"), idioma="en")
    assert repo.guardar([original]) == 1
    leida = repo.obtener(original.oferta.clave)

    assert leida.oferta == original.oferta
    assert leida.puntaje == original.puntaje
    assert leida.vista_en == AHORA
    assert leida.oferta.publicada_en is not None
    assert leida.oferta.publicada_en.tzinfo is not None


def test_guardar_es_idempotente_y_actualiza_sin_tocar_vista_en(
    repo: RepoOfertasSqlAlchemy,
) -> None:
    primera = _puntuada()
    repo.guardar([primera])

    cambiada = _puntuada(titulo="Backend Developer Python Sr", seniority=Seniority.SENIOR)
    cambiada = replace(cambiada, vista_en=AHORA + timedelta(days=1))
    assert repo.guardar([cambiada]) == 0

    leida = repo.obtener(primera.oferta.clave)
    assert leida.oferta.titulo == "Backend Developer Python Sr"
    assert leida.puntaje == cambiada.puntaje
    assert leida.vista_en == AHORA, "vista_en registra la primera aparición"


def test_guardar_lote_con_nuevas_y_existentes(repo: RepoOfertasSqlAlchemy) -> None:
    repo.guardar([_puntuada(id_externo="a")])
    assert repo.guardar([_puntuada(id_externo="a"), _puntuada(id_externo="b")]) == 1
    assert repo.guardar([]) == 0


def test_listar_ordena_y_filtra(repo: RepoOfertasSqlAlchemy) -> None:
    repo.guardar(
        [
            _puntuada(id_externo="alta"),
            _puntuada(id_externo="media", modalidad=Modalidad.PRESENCIAL, paises=("Chile",)),
            _puntuada(id_externo="vieja", publicada_en=AHORA - timedelta(days=3)),
            _puntuada(id_externo="descartada", titulo="Ventas"),
        ]
    )
    claves = [p.oferta.id_externo for p in repo.listar(FiltroOfertas())]
    # A igual puntaje, la publicada más recientemente va primero.
    assert claves == ["alta", "vieja", "media"]

    assert len(repo.listar(FiltroOfertas(incluir_descartadas=True))) == 4
    assert [p.oferta.id_externo for p in repo.listar(FiltroOfertas(min_puntaje=90))] == [
        "alta",
        "vieja",
    ]
    assert len(repo.listar(FiltroOfertas(limite=1))) == 1


def test_listar_filtra_por_idioma(repo: RepoOfertasSqlAlchemy) -> None:
    repo.guardar(
        [
            _puntuada(id_externo="es", idioma="es"),
            _puntuada(id_externo="en", idioma="en"),
            _puntuada(id_externo="sin", idioma=None),
        ]
    )

    def ids(idioma: str | None) -> set[str]:
        return {p.oferta.id_externo for p in repo.listar(FiltroOfertas(idioma=idioma))}

    assert ids(None) == {"es", "en", "sin"}
    assert ids("en") == {"en"}
    assert ids(IDIOMA_NO_INDICA) == {"sin"}
    assert ids("pt") == set()


def test_obtener_inexistente(repo: RepoOfertasSqlAlchemy) -> None:
    with pytest.raises(OfertaNoEncontradaError):
        repo.obtener("falsa:no-existe")


def test_disponible(repo: RepoOfertasSqlAlchemy) -> None:
    assert repo.disponible() is True


def test_no_disponible_si_la_base_no_responde_y_sin_colgarse() -> None:
    """Regresión: sin connect_timeout, /ready tardó 130 s con la base caída (2026-11-25)."""
    motor = crear_motor("postgresql+psycopg://x:x@127.0.0.1:1/x", timeout_conexion_s=2)
    repo = RepoOfertasSqlAlchemy(sessionmaker(motor))
    inicio = time.monotonic()
    assert repo.disponible() is False
    assert time.monotonic() - inicio < 15
    motor.dispose()


def test_marcar_vencidas_y_revivir(repo: RepoOfertasSqlAlchemy) -> None:
    repo.guardar([_puntuada(id_externo="a"), _puntuada(id_externo="b"),
                  _puntuada(fuente="otra", id_externo="c")])  # fmt: skip
    momento = AHORA + timedelta(days=1)
    assert repo.marcar_vencidas("falsa", ["falsa:a"], momento) == 1
    assert repo.marcar_vencidas("falsa", ["falsa:a"], momento) == 0, "idempotente"

    assert [p.oferta.clave for p in repo.listar(FiltroOfertas())] == ["falsa:a", "otra:c"]
    vencida = repo.obtener("falsa:b")
    assert vencida.vencida_en == momento
    assert len(repo.listar(FiltroOfertas(incluir_vencidas=True))) == 3

    repo.guardar([_puntuada(id_externo="b")])  # reapareció en la fuente
    assert repo.obtener("falsa:b").vencida_en is None


def test_marcar_vencidas_sin_vigentes_vence_toda_la_fuente(repo: RepoOfertasSqlAlchemy) -> None:
    repo.guardar([_puntuada(id_externo="a"), _puntuada(fuente="otra", id_externo="c")])
    assert repo.marcar_vencidas("falsa", [], AHORA) == 1
    assert repo.obtener("otra:c").vencida_en is None
