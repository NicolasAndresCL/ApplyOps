"""Vencimiento de ofertas: columna `vencida_en` e índice por fuente.

Expand puro (columna nullable): compatible con la versión anterior de la app,
que simplemente la ignora.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("ofertas", sa.Column("vencida_en", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_ofertas_fuente", "ofertas", ["fuente"])


def downgrade() -> None:
    op.drop_index("ix_ofertas_fuente", table_name="ofertas")
    op.drop_column("ofertas", "vencida_en")
