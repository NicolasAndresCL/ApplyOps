"""Punto de entrada de la UI: `python -m applyops.adapters.inbound.ui.main`.

Composition root de la interfaz: lee `UiSettings`, monta los assets de los temas
si existen, crea el cliente de la API y arranca NiceGUI. Es un proceso aparte de
la API (otro servicio en Docker Compose, con la misma imagen).

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

import logging
import secrets
from pathlib import Path

from nicegui import app, ui
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from applyops.adapters.inbound.ui.cliente import ClienteApi
from applyops.adapters.inbound.ui.temas import AssetsTema
from applyops.adapters.inbound.ui.temas.assets import RUTA_HTTP
from applyops.adapters.inbound.ui.vistas import construir_raiz
from applyops.infra.logs import configurar_logs

logger = logging.getLogger(__name__)

LARGO_MINIMO_SECRETO = 16


class UiSettings(BaseSettings):
    """Variables de entorno de la UI."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_url: str = "http://127.0.0.1:8000"
    ui_host: str = "127.0.0.1"
    ui_puerto: int = Field(default=8080, ge=1, le=65535)
    # Firma la cookie de sesión donde se guarda el tema elegido. Sin valor fijo, se
    # genera uno por proceso y el tema vuelve al de por defecto al reiniciar.
    ui_storage_secret: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    temas_assets_dir: Path = Path("assets/temas")
    log_level: str = "INFO"

    @field_validator("ui_storage_secret")
    @classmethod
    def _secreto(cls, valor: str) -> str:
        # Compose pasa la variable vacía cuando no está en .env: se trata como ausente.
        if not valor:
            return secrets.token_urlsafe(32)
        if len(valor) < LARGO_MINIMO_SECRETO:
            raise ValueError(
                f"UI_STORAGE_SECRET debe tener al menos {LARGO_MINIMO_SECRETO} caracteres"
            )
        return valor


def iniciar() -> None:
    settings = UiSettings()
    configurar_logs(settings.log_level)
    assets = AssetsTema(settings.temas_assets_dir)
    if assets.disponibles:
        app.add_static_files(RUTA_HTTP, settings.temas_assets_dir)
    else:
        logger.warning(
            "Sin assets de temas: se usan solo los colores",
            extra={"carpeta": str(settings.temas_assets_dir)},
        )
    cliente = ClienteApi(settings.api_url)
    app.on_shutdown(cliente.cerrar)
    logger.info("UI iniciando", extra={"api_url": settings.api_url, "puerto": settings.ui_puerto})
    ui.run(
        construir_raiz(cliente, assets),
        host=settings.ui_host,
        port=settings.ui_puerto,
        title="ApplyOps",
        favicon="🎯",
        dark=True,
        language="es",
        storage_secret=settings.ui_storage_secret,
        reload=False,
        show=False,
    )


if __name__ in {"__main__", "__mp_main__"}:
    iniciar()
