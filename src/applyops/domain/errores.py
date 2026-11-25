"""Errores tipados del dominio de ApplyOps.

Cada error es distinguible por el llamador: la API los traduce a un código HTTP
en un handler central (uno por tipo) y la recolección decide si degradar o
cortar según el tipo, sin inspeccionar mensajes.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations


class ApplyOpsError(Exception):
    """Raíz de todos los errores propios: lo que no herede de acá es un bug."""

    codigo = "error_interno"


class OfertaInvalidaError(ApplyOpsError):
    """Los datos de una oferta violan una invariante (título vacío, sueldo invertido…)."""

    codigo = "oferta_invalida"


class PerfilInvalidoError(ApplyOpsError):
    """El archivo de criterios de búsqueda no existe o no cumple el esquema."""

    codigo = "perfil_invalido"


class FuenteNoDisponibleError(ApplyOpsError):
    """Una fuente de ofertas no respondió bien tras agotar los reintentos.

    La recolección la trata como degradación: esa fuente queda fuera del ciclo y
    las demás siguen.
    """

    codigo = "fuente_no_disponible"

    def __init__(self, fuente: str, motivo: str) -> None:
        super().__init__(f"{fuente}: {motivo}")
        self.fuente = fuente
        self.motivo = motivo


class OfertaNoEncontradaError(ApplyOpsError):
    """No existe una oferta con esa clave."""

    codigo = "oferta_no_encontrada"

    def __init__(self, clave: str) -> None:
        super().__init__(f"No existe la oferta {clave!r}")
        self.clave = clave


class RecoleccionEnCursoError(ApplyOpsError):
    """Ya hay una recolección corriendo; lanzar otra duplicaría llamadas a las fuentes."""

    codigo = "recoleccion_en_curso"

    def __init__(self) -> None:
        super().__init__("Ya hay una recolección en curso; espera a que termine")
