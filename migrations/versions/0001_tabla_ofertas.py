"""Tabla de ofertas puntuadas.

Revision ID: 0001
Revises:
Create Date: 2026-11-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ofertas",
        sa.Column("clave", sa.String(300), primary_key=True),
        sa.Column("fuente", sa.String(50), nullable=False),
        sa.Column("id_externo", sa.String(250), nullable=False),
        sa.Column("titulo", sa.String(300), nullable=False),
        sa.Column("empresa", sa.String(200), nullable=False),
        sa.Column("url", sa.String(1000), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("modalidad", sa.String(20), nullable=False),
        sa.Column("paises", sa.JSON(), nullable=False),
        sa.Column("sueldo_min_usd", sa.Integer(), nullable=True),
        sa.Column("sueldo_max_usd", sa.Integer(), nullable=True),
        sa.Column("seniority", sa.String(20), nullable=True),
        sa.Column("idioma", sa.String(5), nullable=True),
        sa.Column("publicada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("puntaje", sa.Integer(), nullable=False),
        sa.Column("descarte", sa.String(300), nullable=True),
        sa.Column("componentes", sa.JSON(), nullable=False),
        sa.Column("vista_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actualizada_en", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ofertas_puntaje", "ofertas", ["puntaje"])


def downgrade() -> None:
    op.drop_index("ix_ofertas_puntaje", table_name="ofertas")
    op.drop_table("ofertas")
