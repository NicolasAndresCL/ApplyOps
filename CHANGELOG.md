# Changelog

Todos los cambios relevantes de ApplyOps. Formato
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y
[versionado semántico](https://semver.org/lang/es/).

## [Sin publicar]

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
