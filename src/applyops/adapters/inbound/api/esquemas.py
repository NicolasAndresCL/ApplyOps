"""Esquemas de salida de la API: son el contrato publicado en `/docs`.

Se separan de las dataclasses del dominio a propósito: el dominio puede
cambiar por dentro sin romper a los clientes (la UI NiceGUI, n8n), y un cambio
acá es un cambio de contrato que se versiona.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from applyops.application.recolectar import ResumenRecoleccion
from applyops.domain.scoring import OfertaPuntuada


class ComponenteSalida(BaseModel):
    nombre: str
    puntos: float
    maximo: float
    detalle: str


class OfertaResumenSalida(BaseModel):
    """Fila de la bandeja: lo necesario para decidir si abrir la oferta."""

    clave: str
    fuente: str
    titulo: str
    empresa: str
    url: str
    modalidad: str
    paises: list[str]
    sueldo_min_usd: int | None
    sueldo_max_usd: int | None
    seniority: str | None
    publicada_en: datetime | None
    puntaje: int
    descarte: str | None
    vista_en: datetime

    @classmethod
    def desde(cls, p: OfertaPuntuada) -> OfertaResumenSalida:
        o = p.oferta
        return cls(
            clave=o.clave,
            fuente=o.fuente,
            titulo=o.titulo,
            empresa=o.empresa,
            url=o.url,
            modalidad=o.modalidad.value,
            paises=list(o.paises),
            sueldo_min_usd=o.sueldo_min_usd,
            sueldo_max_usd=o.sueldo_max_usd,
            seniority=o.seniority.value if o.seniority else None,
            publicada_en=o.publicada_en,
            puntaje=p.puntaje.total,
            descarte=p.puntaje.descarte,
            vista_en=p.vista_en,
        )


class OfertaDetalleSalida(OfertaResumenSalida):
    """Detalle: suma la descripción y el desglose del puntaje."""

    descripcion: str
    idioma: str | None
    componentes: list[ComponenteSalida]

    @classmethod
    def desde(cls, p: OfertaPuntuada) -> OfertaDetalleSalida:
        base = OfertaResumenSalida.desde(p).model_dump()
        return cls(
            **base,
            descripcion=p.oferta.descripcion,
            idioma=p.oferta.idioma,
            componentes=[
                ComponenteSalida(
                    nombre=c.nombre, puntos=round(c.puntos, 2), maximo=c.maximo, detalle=c.detalle
                )
                for c in p.puntaje.componentes
            ],
        )


class ResultadoFuenteSalida(BaseModel):
    fuente: str
    encontradas: int
    nuevas: int
    error: str | None


class ResumenRecoleccionSalida(BaseModel):
    inicio: datetime
    fin: datetime
    total_nuevas: int
    resultados: list[ResultadoFuenteSalida]

    @classmethod
    def desde(cls, r: ResumenRecoleccion) -> ResumenRecoleccionSalida:
        return cls(
            inicio=r.inicio,
            fin=r.fin,
            total_nuevas=r.total_nuevas,
            resultados=[
                ResultadoFuenteSalida(
                    fuente=x.fuente, encontradas=x.encontradas, nuevas=x.nuevas, error=x.error
                )
                for x in r.resultados
            ],
        )


class ErrorSalida(BaseModel):
    codigo: str
    mensaje: str


class RespuestaError(BaseModel):
    """Forma única de todo error de la API: `{"error": {"codigo", "mensaje"}}`."""

    error: ErrorSalida
