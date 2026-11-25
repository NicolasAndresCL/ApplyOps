# Runbook — una fuente de ofertas no entrega datos

**SLO:** cada fuente activa entrega ofertas con menos de 24 h de antigüedad.

## Qué significa

Un ciclo de recolección marcó una fuente como degradada: el resumen de `POST /recolecciones` trae
`"error"` no nulo para esa fuente (con la consulta que falló: `«backend»: timeout tras 3 intentos`), y el
log tiene la línea `Fuente degradada: se guarda lo que respondió`. Lo que trajeron las demás consultas sí
se guardó, y las demás fuentes siguieron funcionando: a la bandeja le faltan solo las ofertas de las
consultas caídas.

Mientras una fuente responda parcial, **no se vence ninguna de sus ofertas** (faltar no prueba que se
cerraron). Si queda degradada varios ciclos, las ofertas cerradas de esa fuente siguen visibles.

## Cómo diagnosticar

1. **Ver el motivo exacto** en los logs JSON de la API (el `correlation_id` agrupa todo el ciclo):

   ```bash
   docker compose logs api --no-log-prefix | grep '"fuente": "getonboard"'
   ```

   | `motivo` | Significa |
   |---|---|
   | `timeout tras N intentos` | La fuente está lenta o caída. Suele ser transitorio. |
   | `HTTP 5xx tras N intentos` / `HTTP 429 …` | Caída o límite de tasa. Ya se respetó su `Retry-After` (tope 60 s). |
   | `'meta' no es un objeto` | **Cambió el contrato** de la paginación. |
   | `HTTP 4xx (no se reintenta)` | La URL o los parámetros dejaron de ser válidos: **cambió la API**. |
   | `respuesta sin la lista 'data'` / `no es JSON válido` | **Cambió el contrato** o hay una página de mantención. |

2. **Probar la fuente a mano**, fuera de la app:

   ```bash
   curl -s "https://www.getonbrd.com/api/v0/search/jobs?query=python&per_page=1" | head -c 400
   ```

3. **Muchas ofertas omitidas** (warning `Oferta con forma inesperada, se omite` repetido): la fuente
   responde, pero cambió la forma de las ofertas.

## Cómo mitigar

- **Transitorio (timeout, 5xx, 429):** no hacer nada; el próximo ciclo reintenta. Si se repite más de
  24 h, bajar la frecuencia (`RECOLECCION_INTERVALO_HORAS`) o subir `HTTP_TIMEOUT_SEGUNDOS`.
- **Cambio de contrato (4xx, sin `data`, ofertas omitidas):**
  1. Capturar una respuesta nueva como fixture en `tests/fixtures/`.
  2. Ajustar `mapear_oferta` en el adaptador hasta que el contract test pase.
  3. PR con el fixture nuevo y la regresión.
- Mientras tanto, la app sigue sirviendo las ofertas ya guardadas y las de las otras fuentes.
