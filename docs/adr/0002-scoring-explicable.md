# ADR 0002 — Scoring determinista y explicable, sin LLM

- **Estado:** aceptada
- **Fecha:** 2026-11-25

## Contexto

Hay que ordenar cientos de ofertas para decidir a cuáles 5–10 postular cada semana. Dos opciones: pedirle
a un LLM que puntúe cada oferta, o reglas deterministas configurables.

## Decisión

El scoring es una **función pura** del dominio (`domain/scoring.py`): 0–100, suma de cinco componentes
con máximos configurables en `perfil/busqueda.yaml`, y un **desglose legible** de cada componente.

- **Determinista**: la misma oferta y el mismo perfil dan siempre el mismo puntaje. Se testea sin red y
  se puede re-puntuar todo el histórico al cambiar el perfil, gratis.
- **Explicable**: cada componente dice qué sumó («Pide: Python, Docker»; «USD 2.800–3.000: sobre tu
  mínimo»). Un número sin el porqué no sirve para decidir.
- **Lo desconocido no es cero**: el 58 % de las ofertas de Get on Board no publica sueldo (muestra del
  2026-11-25). Penalizarlas a cero las hundiría por falta de dato. Reciben la mitad del componente y se
  marca.
- **Descartar no es borrar**: la oferta descartada queda con total 0, su motivo y su desglose, visible
  con `incluir_descartadas=true`.
- El LLM se reserva para lo que sí necesita lenguaje: adaptar CV y carta (hito 3).

## Consecuencias

- El matching de skills es por palabra completa con sinónimos: no entiende contexto («no se requiere
  Python» suma Python). Es aceptable para priorizar; la decisión final es humana.
- Ajustar el criterio es editar un YAML, no reentrenar ni gastar tokens.
