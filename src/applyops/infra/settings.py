"""Configuración de ApplyOps, leída del entorno y validada al arrancar (12-factor).

Ningún módulo lee `os.environ` por su cuenta: todo pasa por `Settings`, que
falla al arrancar si falta algo obligatorio, no a la primera request.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Variables de entorno (o `.env`). Los nombres van en mayúsculas en el entorno."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field(description="URL SQLAlchemy, p. ej. postgresql+psycopg://…")
    perfil_busqueda_path: Path = Path("perfil/busqueda.yaml")
    recoleccion_intervalo_horas: float = Field(default=0, ge=0)
    http_timeout_segundos: float = Field(default=15, gt=0)
    http_reintentos: int = Field(default=3, ge=1, le=6)
    getonboard_url_base: str = "https://www.getonbrd.com/api/v0"
    getonboard_max_paginas: int = Field(default=4, ge=1, le=20)
    log_level: str = "INFO"
