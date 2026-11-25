"""Repositorio de ofertas sobre SQLAlchemy: implementa el puerto `RepoOfertas`.

`guardar` es idempotente: consulta en una sola query qué claves ya existen,
inserta las nuevas y actualiza las demás (la oferta pudo cambiar en la fuente,
o cambió el perfil y con él el puntaje), sin tocar `vista_en`, que registra
cuándo apareció por primera vez.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from applyops.adapters.outbound.modelos_sqlalchemy import OfertaFila
from applyops.domain.errores import OfertaNoEncontradaError
from applyops.domain.oferta import Modalidad, Oferta, Seniority
from applyops.domain.puertos import FiltroOfertas
from applyops.domain.scoring import Componente, OfertaPuntuada, Puntaje


class RepoOfertasSqlAlchemy:
    """Persistencia de ofertas puntuadas en cualquier motor que soporte SQLAlchemy."""

    def __init__(
        self,
        sesiones: sessionmaker[Session],
        reloj: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._sesiones = sesiones
        self._reloj = reloj

    def guardar(self, puntuadas: Sequence[OfertaPuntuada]) -> int:
        if not puntuadas:
            return 0
        ahora = self._reloj()
        claves = [p.oferta.clave for p in puntuadas]
        with self._sesiones.begin() as sesion:
            existentes = {
                f.clave: f
                for f in sesion.scalars(select(OfertaFila).where(OfertaFila.clave.in_(claves)))
            }
            nuevas = 0
            for puntuada in puntuadas:
                fila = existentes.get(puntuada.oferta.clave)
                if fila is None:
                    fila = OfertaFila(clave=puntuada.oferta.clave, vista_en=puntuada.vista_en)
                    sesion.add(fila)
                    existentes[fila.clave] = fila
                    nuevas += 1
                _copiar(puntuada, fila, ahora)
        return nuevas

    def listar(self, filtro: FiltroOfertas) -> list[OfertaPuntuada]:
        consulta = select(OfertaFila).where(OfertaFila.puntaje >= filtro.min_puntaje)
        if not filtro.incluir_descartadas:
            consulta = consulta.where(OfertaFila.descarte.is_(None))
        consulta = consulta.order_by(
            OfertaFila.puntaje.desc(),
            OfertaFila.publicada_en.desc().nulls_last(),
            OfertaFila.clave,
        ).limit(filtro.limite)
        with self._sesiones() as sesion:
            return [_a_dominio(f) for f in sesion.scalars(consulta)]

    def obtener(self, clave: str) -> OfertaPuntuada:
        with self._sesiones() as sesion:
            fila = sesion.get(OfertaFila, clave)
            if fila is None:
                raise OfertaNoEncontradaError(clave)
            return _a_dominio(fila)

    def disponible(self) -> bool:
        try:
            with self._sesiones() as sesion:
                sesion.execute(text("SELECT 1"))
        except SQLAlchemyError:
            return False
        return True


def _copiar(puntuada: OfertaPuntuada, fila: OfertaFila, ahora: datetime) -> None:
    o, p = puntuada.oferta, puntuada.puntaje
    fila.fuente = o.fuente
    fila.id_externo = o.id_externo
    fila.titulo = o.titulo
    fila.empresa = o.empresa
    fila.url = o.url
    fila.descripcion = o.descripcion
    fila.modalidad = o.modalidad.value
    fila.paises = list(o.paises)
    fila.sueldo_min_usd = o.sueldo_min_usd
    fila.sueldo_max_usd = o.sueldo_max_usd
    fila.seniority = o.seniority.value if o.seniority else None
    fila.idioma = o.idioma
    fila.publicada_en = o.publicada_en
    fila.puntaje = p.total
    fila.descarte = p.descarte
    fila.componentes = [_componente_a_json(c) for c in p.componentes]
    fila.actualizada_en = ahora


def _componente_a_json(c: Componente) -> dict[str, Any]:
    return {"nombre": c.nombre, "puntos": c.puntos, "maximo": c.maximo, "detalle": c.detalle}


def _con_zona(fecha: datetime | None) -> datetime | None:
    # SQLite devuelve fechas sin zona aunque se guarden con ella; todas se guardan en UTC.
    if fecha is not None and fecha.tzinfo is None:
        return fecha.replace(tzinfo=UTC)
    return fecha


def _a_dominio(fila: OfertaFila) -> OfertaPuntuada:
    oferta = Oferta(
        fuente=fila.fuente,
        id_externo=fila.id_externo,
        titulo=fila.titulo,
        empresa=fila.empresa,
        url=fila.url,
        descripcion=fila.descripcion,
        modalidad=Modalidad(fila.modalidad),
        paises=tuple(fila.paises),
        sueldo_min_usd=fila.sueldo_min_usd,
        sueldo_max_usd=fila.sueldo_max_usd,
        seniority=Seniority(fila.seniority) if fila.seniority else None,
        idioma=fila.idioma,
        publicada_en=_con_zona(fila.publicada_en),
    )
    puntaje = Puntaje(
        total=fila.puntaje,
        componentes=tuple(Componente(**c) for c in fila.componentes),
        descarte=fila.descarte,
    )
    vista_en = fila.vista_en if fila.vista_en.tzinfo else fila.vista_en.replace(tzinfo=UTC)
    return OfertaPuntuada(oferta=oferta, puntaje=puntaje, vista_en=vista_en)
