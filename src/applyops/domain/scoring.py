"""Scoring de ofertas contra el perfil: función pura, explicable y sin I/O.

El puntaje (0–100) es la suma de cinco componentes (stack, modalidad, sueldo,
seniority, idioma), cada uno con su máximo definido en `PesosScoring`. Cada
componente trae un `detalle` legible, porque un número sin el porqué no ayuda
a decidir a qué postular.

Dos reglas de diseño:
- **Lo desconocido no es cero.** El 58 % de las ofertas de Get on Board no
  publica sueldo (muestra del 2026-11-25); penalizarlas a cero las hundiría a
  todas por falta de dato, no por ser malas. Se les da la mitad y se marca.
- **Descartar no borra.** Una oferta descartada (palabra excluida en el título,
  presencial fuera de los países aceptados) queda con total 0 pero conserva el
  desglose, para que se pueda revisar por qué se descartó.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from functools import cache

from applyops.domain.oferta import Modalidad, Oferta
from applyops.domain.perfil import PUNTAJE_MAXIMO, PerfilBusqueda

# Fracción otorgada cuando la oferta no informa el dato (ver docstring del módulo).
FRACCION_DATO_DESCONOCIDO = 0.5
# Modalidades que obligan a vivir (o estar) en ciertos países.
MODALIDADES_CON_PAIS = frozenset({Modalidad.HIBRIDO, Modalidad.PRESENCIAL, Modalidad.REMOTO_LOCAL})


@dataclass(frozen=True, slots=True)
class Componente:
    """Un aporte al puntaje con su explicación."""

    nombre: str
    puntos: float
    maximo: float
    detalle: str


@dataclass(frozen=True, slots=True)
class Puntaje:
    """Resultado del scoring. `descarte` trae el motivo si la oferta quedó fuera."""

    total: int
    componentes: tuple[Componente, ...]
    descarte: str | None = None

    @property
    def descartada(self) -> bool:
        return self.descarte is not None


@dataclass(frozen=True, slots=True)
class OfertaPuntuada:
    """Una oferta junto a su puntaje, cuándo se vio por primera vez y si venció.

    `vencida_en` se fija cuando una recolección completa de su fuente ya no la trae
    (la oferta se cerró o se despublicó); vuelve a `None` si reaparece.
    """

    oferta: Oferta
    puntaje: Puntaje
    vista_en: datetime
    vencida_en: datetime | None = None


def normalizar(texto: str) -> str:
    """Minúsculas y sin tildes, para que «Automatización» calce con «automatizacion»."""
    sin_tildes = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in sin_tildes if not unicodedata.combining(c)).casefold()


@cache
def _patron(termino: str) -> re.Pattern[str]:
    # Límites propios en vez de \b: \b falla con términos que terminan en símbolo
    # («c#», «ci/cd», «node.js») porque entre dos no-palabras no hay frontera.
    return re.compile(rf"(?<![\w]){re.escape(normalizar(termino))}(?![\w])")


def menciona(texto_normalizado: str, termino: str) -> bool:
    """¿El texto (ya normalizado) menciona el término como palabra completa?"""
    return _patron(termino).search(texto_normalizado) is not None


def puntuar(oferta: Oferta, perfil: PerfilBusqueda) -> Puntaje:
    """Puntúa una oferta contra el perfil. Determinista: misma entrada, mismo puntaje."""
    componentes = (
        _stack(oferta, perfil),
        _modalidad(oferta, perfil),
        _sueldo(oferta, perfil),
        _seniority(oferta, perfil),
        _idioma(oferta, perfil),
    )
    descarte = _motivo_descarte(oferta, perfil)
    if descarte is not None:
        return Puntaje(total=0, componentes=componentes, descarte=descarte)
    total = round(sum(c.puntos for c in componentes))
    return Puntaje(total=max(0, min(PUNTAJE_MAXIMO, total)), componentes=componentes)


def _motivo_descarte(oferta: Oferta, perfil: PerfilBusqueda) -> str | None:
    titulo = normalizar(oferta.titulo)
    for palabra in perfil.palabras_descarte:
        if menciona(titulo, palabra):
            return f"El título contiene «{palabra}»"
    requiere_pais = oferta.modalidad in MODALIDADES_CON_PAIS
    if requiere_pais and oferta.paises and not _en_paises_aceptados(oferta, perfil):
        return f"{oferta.modalidad.value} en {', '.join(oferta.paises)}: fuera de tus países"
    return None


def _en_paises_aceptados(oferta: Oferta, perfil: PerfilBusqueda) -> bool:
    aceptados = {normalizar(p) for p in perfil.paises_presenciales}
    return any(normalizar(p) in aceptados for p in oferta.paises)


def _stack(oferta: Oferta, perfil: PerfilBusqueda) -> Componente:
    maximo = perfil.pesos.stack
    texto = normalizar(f"{oferta.titulo}\n{oferta.descripcion}")
    encontradas = [s for s in perfil.skills if any(menciona(texto, t) for t in s.terminos)]
    peso = sum(s.peso for s in encontradas)
    fraccion = min(1.0, peso / perfil.saturacion_stack)
    if encontradas:
        detalle = "Pide: " + ", ".join(s.nombre for s in encontradas)
    else:
        detalle = "No menciona ninguna skill del perfil"
    return Componente("stack", maximo * fraccion, maximo, detalle)


def _modalidad(oferta: Oferta, perfil: PerfilBusqueda) -> Componente:
    maximo = perfil.pesos.modalidad
    if oferta.modalidad is Modalidad.DESCONOCIDA:
        return Componente(
            "modalidad", maximo * FRACCION_DATO_DESCONOCIDO, maximo, "Modalidad no informada"
        )
    factor = perfil.factor_modalidad.get(oferta.modalidad, 0.0)
    lugar = f" ({', '.join(oferta.paises)})" if oferta.paises else ""
    return Componente("modalidad", maximo * factor, maximo, f"{oferta.modalidad.value}{lugar}")


def _sueldo(oferta: Oferta, perfil: PerfilBusqueda) -> Componente:
    maximo = perfil.pesos.sueldo
    minimo_perfil = perfil.sueldo_minimo_usd
    piso = oferta.sueldo_min_usd if oferta.sueldo_min_usd is not None else oferta.sueldo_max_usd
    tope = oferta.sueldo_max_usd if oferta.sueldo_max_usd is not None else oferta.sueldo_min_usd
    if piso is None or tope is None:
        return Componente(
            "sueldo", maximo * FRACCION_DATO_DESCONOCIDO, maximo, "Sueldo no publicado"
        )
    rango = f"USD {piso:,}–{tope:,}".replace(",", ".")
    if minimo_perfil is None:
        return Componente("sueldo", maximo, maximo, f"{rango} (sin mínimo definido)")
    if tope < minimo_perfil:
        return Componente("sueldo", 0.0, maximo, f"{rango}: bajo tu mínimo")
    if piso >= minimo_perfil:
        return Componente("sueldo", maximo, maximo, f"{rango}: sobre tu mínimo")
    # El rango cruza el mínimo: vale la parte del rango que queda por encima.
    fraccion = (tope - minimo_perfil) / (tope - piso)
    return Componente("sueldo", maximo * fraccion, maximo, f"{rango}: cruza tu mínimo")


def _seniority(oferta: Oferta, perfil: PerfilBusqueda) -> Componente:
    maximo = perfil.pesos.seniority
    if oferta.seniority is None:
        return Componente(
            "seniority", maximo * FRACCION_DATO_DESCONOCIDO, maximo, "Seniority no informado"
        )
    factor = perfil.factor_seniority.get(oferta.seniority, 0.0)
    return Componente("seniority", maximo * factor, maximo, oferta.seniority.value)


def _idioma(oferta: Oferta, perfil: PerfilBusqueda) -> Componente:
    maximo = perfil.pesos.idioma
    if oferta.idioma is None:
        return Componente("idioma", maximo, maximo, "Idioma no especificado")
    if oferta.idioma in perfil.idiomas:
        return Componente("idioma", maximo, maximo, oferta.idioma)
    return Componente("idioma", 0.0, maximo, f"{oferta.idioma}: no está en tus idiomas")
