"""Normalización de URL para la clave de las ofertas cargadas a mano.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

import pytest

from applyops.application.registrar_manual import LARGO_ID, id_desde_url


@pytest.mark.parametrize(
    "variante",
    [
        "https://www.linkedin.com/jobs/view/123",
        "https://www.linkedin.com/jobs/view/123/",
        "https://WWW.LinkedIn.com/jobs/view/123?trk=public_jobs",
        "  https://www.linkedin.com/jobs/view/123#detalle  ",
    ],
)
def test_misma_oferta_mismo_id(variante: str) -> None:
    assert id_desde_url(variante) == id_desde_url("https://www.linkedin.com/jobs/view/123")


def test_ofertas_distintas_ids_distintos() -> None:
    assert id_desde_url("https://x.cl/ofertas/1") != id_desde_url("https://x.cl/ofertas/2")


def test_largo_fijo() -> None:
    assert len(id_desde_url("https://x.cl/a")) == LARGO_ID
