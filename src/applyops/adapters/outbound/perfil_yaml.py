"""Carga `perfil/busqueda.yaml` y lo convierte en `PerfilBusqueda` del dominio.

El esquema se valida con Pydantic al arrancar: un perfil mal escrito (factor
fuera de 0–1, modalidad inexistente, clave mal tipeada) detiene el arranque con
un mensaje claro, en vez de producir puntajes raros en silencio.

Si el archivo real no existe se usa el ejemplo versionado y se avisa en el
log: así la app arranca en un clon limpio (CI, Docker) sin datos personales.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from applyops.domain.errores import PerfilInvalidoError
from applyops.domain.oferta import Modalidad, Seniority
from applyops.domain.perfil import PerfilBusqueda, PesosScoring, Skill

logger = logging.getLogger(__name__)

ARCHIVO_EJEMPLO = "busqueda.example.yaml"


class _Esquema(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class _SkillYaml(_Esquema):
    nombre: str = Field(min_length=1)
    peso: int = Field(default=1, ge=1, le=3)
    sinonimos: tuple[str, ...] = ()


class _PesosYaml(_Esquema):
    stack: int = Field(default=50, ge=0)
    modalidad: int = Field(default=20, ge=0)
    sueldo: int = Field(default=15, ge=0)
    seniority: int = Field(default=10, ge=0)
    idioma: int = Field(default=5, ge=0)


class _PerfilYaml(_Esquema):
    consultas: tuple[str, ...] = Field(min_length=1)
    skills: tuple[_SkillYaml, ...] = Field(min_length=1)
    saturacion_stack: int = Field(default=10, ge=1)
    sueldo_minimo_usd: int | None = Field(default=None, ge=0)
    modalidad: dict[Modalidad, float] = Field(default_factory=dict)
    paises_presenciales: tuple[str, ...] = ()
    seniority: dict[Seniority, float] = Field(default_factory=dict)
    idiomas: tuple[str, ...] = ("es",)
    palabras_descarte: tuple[str, ...] = ()
    pesos: _PesosYaml = _PesosYaml()


def resolver_ruta(ruta: Path) -> Path:
    """La ruta pedida si existe; si no, el ejemplo de la misma carpeta (con aviso)."""
    if ruta.is_file():
        return ruta
    ejemplo = ruta.with_name(ARCHIVO_EJEMPLO)
    if ejemplo.is_file():
        logger.warning(
            "No existe el perfil real; se usa el ejemplo versionado",
            extra={"pedido": str(ruta), "usado": str(ejemplo)},
        )
        return ejemplo
    raise PerfilInvalidoError(f"No existe {ruta} ni {ejemplo}")


def cargar_perfil(ruta: Path) -> PerfilBusqueda:
    """Lee, valida y convierte el perfil. Lanza `PerfilInvalidoError` con el detalle."""
    archivo = resolver_ruta(ruta)
    try:
        crudo = yaml.safe_load(archivo.read_text(encoding="utf-8"))
        datos = _PerfilYaml.model_validate(crudo)
    except yaml.YAMLError as error:
        raise PerfilInvalidoError(f"{archivo}: YAML mal formado: {error}") from error
    except ValidationError as error:
        raise PerfilInvalidoError(f"{archivo}: {error}") from error
    return PerfilBusqueda(
        consultas=datos.consultas,
        skills=tuple(Skill(s.nombre, s.peso, s.sinonimos) for s in datos.skills),
        saturacion_stack=datos.saturacion_stack,
        sueldo_minimo_usd=datos.sueldo_minimo_usd,
        factor_modalidad=dict(datos.modalidad),
        paises_presenciales=datos.paises_presenciales,
        factor_seniority=dict(datos.seniority),
        idiomas=datos.idiomas,
        palabras_descarte=datos.palabras_descarte,
        pesos=PesosScoring(**datos.pesos.model_dump()),
    )
