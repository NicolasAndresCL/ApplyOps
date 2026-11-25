"""Tablas de ApplyOps en SQLAlchemy 2 (estilo declarativo tipado).

Solo el adaptador de persistencia y Alembic importan este módulo: el dominio
no sabe que existe. Los tipos son portables (JSON genérico, no JSONB) para que
los tests de integración corran igual en SQLite y en PostgreSQL.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base declarativa; su `metadata` la usa Alembic para autogenerar migraciones."""


class OfertaFila(Base):
    """Una oferta con su último puntaje. `clave` = `fuente:id_externo` (idempotencia)."""

    __tablename__ = "ofertas"

    clave: Mapped[str] = mapped_column(String(300), primary_key=True)
    fuente: Mapped[str] = mapped_column(String(50))
    id_externo: Mapped[str] = mapped_column(String(250))
    titulo: Mapped[str] = mapped_column(String(300))
    empresa: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(String(1000))
    descripcion: Mapped[str] = mapped_column(Text)
    modalidad: Mapped[str] = mapped_column(String(20))
    paises: Mapped[list[str]] = mapped_column(JSON)
    sueldo_min_usd: Mapped[int | None] = mapped_column(Integer)
    sueldo_max_usd: Mapped[int | None] = mapped_column(Integer)
    seniority: Mapped[str | None] = mapped_column(String(20))
    idioma: Mapped[str | None] = mapped_column(String(5))
    publicada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    puntaje: Mapped[int] = mapped_column(Integer)
    descarte: Mapped[str | None] = mapped_column(String(300))
    componentes: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    vista_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actualizada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Cuándo una recolección completa de su fuente dejó de traerla (cerrada). None = vigente.
    vencida_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_ofertas_puntaje", "puntaje"),
        Index("ix_ofertas_fuente", "fuente"),
    )
