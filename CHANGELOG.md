# Changelog

Todos los cambios relevantes de ApplyOps. Formato
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y
[versionado semántico](https://semver.org/lang/es/).

## [Sin publicar]

## [0.4.0] — 2026-11-25

Filtro por idioma y tema Cian, a partir de la primera prueba de la UI con datos reales.

### Añadido
- (minor) **Filtro por idioma** en la bandeja y en `GET /ofertas?idioma=` (`es`, `en`, `pt` o `no_indica`
  para las que no lo publican). La bandeja suma la columna Idioma y el detalle, su píldora; con el filtro
  puesto y sin resultados, la bandeja lo dice en vez de sugerir recolectar.
- (minor) **Tema 💠 Cian**, con la paleta del portafolio (`#22D3EE` sobre azul noche): fondo aurora,
  degradado cian → índigo → magenta en marca, títulos y menú activo, y glow en las tarjetas. Sin imágenes.

### Cambiado
- `GET /ofertas` devuelve `idioma` en cada oferta (antes solo el detalle). Campo nuevo: compatible.

### Corregido
Revisión automática (Sourcery) del PR #6:
- **Una respuesta vieja ya no pisa el filtro actual**: si cambias un filtro antes de que llegue la
  respuesta anterior, la bandeja solo pinta la del último pedido.
- **El aviso de bandeja vacía ya no culpa al idioma** cuando la lista la vacía otro filtro: dice
  «Ninguna oferta calza con los filtros» y sugiere qué cambiar.
- `FiltroOfertas` rechaza un idioma no soportado al construirse (antes devolvía una lista vacía) e
  `idioma` va al final de su firma y de `ClienteApi.listar_ofertas`, sin correr la posición de `limite`.

## [0.3.1] — 2026-11-25

Correcciones de la revisión automática (Sourcery) del PR #3.

### Corregido
- **Las ofertas cerradas ya no quedan en la bandeja**: tras una recolección completa de una fuente, sus
  ofertas que ya no vienen se marcan vencidas (`vencida_en`, migración `0002`) y dejan de listarse; si
  reaparecen, vuelven. Solo se vence si la respuesta está completa: sin consultas caídas, sin corte
  por el tope de páginas y sin ofertas omitidas (cada fuente lo declara en `ResultadoBusqueda`). Las
  cargadas a mano no vencen. `GET /ofertas?incluir_vencidas=true` las muestra y
  el detalle en la UI avisa que la oferta probablemente se cerró.
- **Una consulta que falla ya no descarta las demás de la misma fuente**: se guarda lo que respondió y la
  fuente se informa como degradada (en ese caso no se vence nada, porque la lista está incompleta).
- **Get on Board**: un `meta` mal formado degrada la consulta en vez de abortar la recolección, y una
  oferta con título nulo o `company` con otra forma se omite (o queda como «desconocida») sin tumbar la
  página.
- **Reintentos**: se reintenta cualquier 5xx (antes solo 500/502/503/504) y se respeta `Retry-After` en
  429/503, con tope de 60 s.
- **Errores**: un error de dominio sin código HTTP ya no devuelve su mensaje interno en el 500; los 404 y
  405 de rutas usan el contrato `{"error": …}` (`ruta_no_encontrada`, `metodo_no_permitido`, con su
  cabecera `Allow`), y un 5xx lanzado como `HTTPException` tampoco expone su detalle.
- **Docker Compose** pasa a la API `HTTP_TIMEOUT_SEGUNDOS`, `HTTP_REINTENTOS`, `GETONBOARD_URL_BASE` y
  `GETONBOARD_MAX_PAGINAS`: configurarlas en `.env` antes no tenía efecto.
- **Perfil**: se rechazan pesos negativos aunque sumen 100.

### Dependencias
- `actions/checkout` 5 → 7 y `actions/setup-python` 6 → 7 en los workflows (Dependabot #1 y #2).

## [0.3.0] — 2026-11-25

### Añadido
- **Interfaz web con NiceGUI 4**, en un proceso aparte que consume la API por HTTP (servicio `ui` en
  Docker Compose, puerto 8080):
  - **Bandeja** priorizada con color por tramo, filtro de puntaje mínimo, «Ver descartadas» y
    **Recolectar ahora**.
  - **Detalle** con el desglose del puntaje por componente y **Abrir la oferta para postular** (el clic
    final sigue siendo humano).
  - **Cargar oferta** a mano para portales sin API (LinkedIn, Indeed, Laborum).
  - **Ajustes**: tema recordado por navegador y estado de la API y de la base.
  - Si la API no responde, cada vista lo muestra con **Reintentar**.
- **Temas copiados de Jaime**: Mugiwara y Gear 5 (Luffy), Esmeralda (Zoro) y Shingeki (Eren), con sus
  paletas, cristal, tipografías, figura y emblema del personaje, y efectos (Haki del Rey, rayo y vapor del
  titán). Cambian en vivo, sin recargar.
- `scripts/importar_temas_jaime.ps1`: copia desde Jaime las imágenes de los temas a `assets/temas/`
  (en `.gitignore`: tienen derechos de autor).
- `POST /ofertas`: alta manual de una oferta, puntuada al guardar. La clave sale de la URL sin
  parámetros de rastreo, así la misma oferta copiada dos veces se actualiza en vez de duplicarse.
- El job de build del CI y `ci_local.ps1` verifican que la UI arranca y responde.

### Cambiado
- Los errores de validación (422) usan el contrato único `{"error": {"codigo": "entrada_invalida", …}}`
  en lugar del `{"detail": […]}` de FastAPI.
- La imagen Docker crea `/app/.nicegui` con permisos del usuario no-root.

## [0.2.0] — 2026-11-25

### Añadido
- **Recolección desde Get on Board** (API pública v0): paginación con tope, deduplicación entre
  consultas e idempotencia por clave natural `fuente:id_externo`.
- **Scoring explicable** de 0 a 100 en cinco componentes (stack, modalidad, sueldo, seniority, idioma)
  con desglose legible y descartes (palabra excluida en el título, híbrido/presencial/remoto local
  fuera de los países aceptados). El dato desconocido no vale cero: sueldo o seniority sin publicar
  reciben la mitad del componente.
- Criterios de búsqueda en `perfil/busqueda.yaml` validados con Pydantic al arrancar
  (`busqueda.example.yaml` versionado como respaldo).
- Persistencia en PostgreSQL con SQLAlchemy 2 y migración Alembic `0001` (tabla `ofertas`).
- API: `GET /ofertas` (bandeja priorizada con filtros), `GET /ofertas/{clave}` (detalle con desglose),
  `POST /recolecciones` (recolección manual con resumen por fuente) y `GET /ready` (503 si la base no
  responde).
- Cliente HTTP resiliente: timeout, reintentos con backoff exponencial y jitter solo ante 429/5xx/red,
  y `FuenteNoDisponibleError` tipado; la recolección degrada la fuente caída y sigue con las demás.
- Recolección programada opcional (`RECOLECCION_INTERVALO_HORAS`) gestionada por el `lifespan`.
- Logs JSON a stdout con `correlation_id` por request (cabecera `X-Correlation-ID`) y por ciclo.
- Contrato de errores único `{"error": {"codigo", "mensaje"}}` (404, 409, 500 sin stack).
- ADR 0002 (scoring explicable) y runbook `fuente-sin-datos`.

### Corregido
- `connect_timeout` de 5 s hacia PostgreSQL: sin él, `/ready` tardaba 130 s en responder con la base
  caída en lugar de devolver 503.
- `countries: ["Remote"]` de Get on Board ya no se interpreta como país: descartaba 62 de 239 ofertas
  reales. En `remote_local` el país exigido se toma de `location_tenants`.

### Cambiado
- La app se levanta con `uvicorn applyops.main:crear_app --factory`: importar `main` ya no lee el
  entorno.
- Puertos del host configurables en Docker Compose (`DB_PUERTO_HOST`, por defecto 5433, para no chocar
  con un PostgreSQL local; `API_PUERTO_HOST`, por defecto 8000).

## [0.1.0] — 2026-11-25

### Añadido
- Esqueleto hexagonal (`domain/`, `application/`, `adapters/`, `infra/`) con FastAPI y
  endpoint `/health`.
- CI en GitHub Actions (lint → tipos → tests → build de la imagen Docker), Dependabot,
  plantillas de issue y PR y workflow de release por tag.
- Dockerfile multi-stage no-root y `docker-compose.yml` con PostgreSQL 16.
- ADR 0001: fuentes legítimas y clic de postular humano.
