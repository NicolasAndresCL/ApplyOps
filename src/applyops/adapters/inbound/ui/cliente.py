"""Cliente HTTP de la UI hacia la API de ApplyOps.

La UI es un adaptador de entrada más: consume la API por HTTP como lo haría n8n
o cualquier otro cliente, y no importa casos de uso por atajo. Así el backend
sigue siendo reutilizable y la UI, reemplazable.

Asíncrono (`httpx.AsyncClient`) para no bloquear el event loop de NiceGUI, con
timeout en toda llamada. Los errores salen tipados:
- `ApiNoDisponibleError`: no hubo respuesta (red, timeout, 5xx). La UI ofrece reintentar.
- `ApiRechazoError`: la API respondió con su contrato de error (`codigo`, `mensaje`).

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

from typing import Any

import httpx

from applyops import __version__

# Una recolección con una fuente tarda ~7 s; con más fuentes, más. El resto es instantáneo.
TIMEOUT_SEGUNDOS = 10.0
TIMEOUT_RECOLECCION_SEGUNDOS = 120.0


class ApiNoDisponibleError(Exception):
    """La API no respondió o falló del lado del servidor."""


class ApiRechazoError(Exception):
    """La API respondió con un error de su contrato (`{"error": {"codigo", "mensaje"}}`)."""

    def __init__(self, estado: int, codigo: str, mensaje: str) -> None:
        super().__init__(mensaje)
        self.estado = estado
        self.codigo = codigo
        self.mensaje = mensaje


class ClienteApi:
    """Operaciones que la UI necesita de la API."""

    def __init__(self, url_base: str, transporte: httpx.AsyncBaseTransport | None = None) -> None:
        self._http = httpx.AsyncClient(
            base_url=url_base.rstrip("/"),
            transport=transporte,
            timeout=TIMEOUT_SEGUNDOS,
            headers={"User-Agent": f"ApplyOps-UI/{__version__}"},
        )

    async def cerrar(self) -> None:
        await self._http.aclose()

    async def listar_ofertas(
        self,
        min_puntaje: int = 0,
        incluir_descartadas: bool = False,
        limite: int = 500,
        idioma: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "min_puntaje": min_puntaje,
            "incluir_descartadas": str(incluir_descartadas).lower(),
            "limite": limite,
        }
        if idioma:
            params["idioma"] = idioma
        datos: list[dict[str, Any]] = await self._pedir("GET", "/ofertas", params=params)
        return datos

    async def obtener_oferta(self, clave: str) -> dict[str, Any]:
        datos: dict[str, Any] = await self._pedir("GET", f"/ofertas/{clave}")
        return datos

    async def registrar_oferta(self, entrada: dict[str, Any]) -> dict[str, Any]:
        datos: dict[str, Any] = await self._pedir("POST", "/ofertas", json=entrada)
        return datos

    async def recolectar(self) -> dict[str, Any]:
        datos: dict[str, Any] = await self._pedir(
            "POST", "/recolecciones", timeout=TIMEOUT_RECOLECCION_SEGUNDOS
        )
        return datos

    async def estado(self) -> dict[str, Any]:
        """Versión de la API (`/health`) y si su base responde (`/ready`), sin lanzar."""
        try:
            salud = await self._http.get("/health")
            listo = await self._http.get("/ready")
        except httpx.HTTPError:
            return {"api": False, "base_de_datos": False, "version": None}
        return {
            "api": salud.status_code == 200,
            "base_de_datos": listo.status_code == 200,
            "version": salud.json().get("version") if salud.status_code == 200 else None,
        }

    async def _pedir(self, metodo: str, ruta: str, **kwargs: Any) -> Any:
        try:
            respuesta = await self._http.request(metodo, ruta, **kwargs)
        except httpx.TimeoutException as error:
            raise ApiNoDisponibleError("La API no respondió a tiempo") from error
        except httpx.HTTPError as error:
            raise ApiNoDisponibleError(
                f"No se pudo conectar con la API ({type(error).__name__})"
            ) from error
        if respuesta.status_code >= 500:
            raise ApiNoDisponibleError(f"La API falló (HTTP {respuesta.status_code})")
        if respuesta.is_error:
            raise _rechazo(respuesta)
        return respuesta.json()


def _rechazo(respuesta: httpx.Response) -> ApiRechazoError:
    try:
        error = respuesta.json()["error"]
        return ApiRechazoError(respuesta.status_code, str(error["codigo"]), str(error["mensaje"]))
    except ValueError, KeyError, TypeError:
        return ApiRechazoError(
            respuesta.status_code, "desconocido", f"HTTP {respuesta.status_code}"
        )
