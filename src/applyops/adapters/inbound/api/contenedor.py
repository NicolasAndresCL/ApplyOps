"""Contenedor de dependencias que los routers reciben por `Depends`.

El composition root (`main.py`) lo arma con las clases concretas y lo deja en
`app.state`; los tests lo arman con fakes. Los routers nunca instancian nada.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from applyops.application.consultar import ConsultarOfertas
from applyops.application.recolectar import RecolectarOfertas
from applyops.domain.puertos import RepoOfertas


@dataclass(frozen=True, slots=True)
class Contenedor:
    recolectar: RecolectarOfertas
    consultar: ConsultarOfertas
    repo: RepoOfertas


def obtener_contenedor(request: Request) -> Contenedor:
    contenedor: Contenedor = request.app.state.contenedor
    return contenedor
