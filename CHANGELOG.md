# Changelog

Todos los cambios relevantes de ApplyOps. Formato
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y
[versionado semántico](https://semver.org/lang/es/).

## [Sin publicar]

## [0.1.0] — 2026-11-25

### Añadido
- Esqueleto hexagonal (`domain/`, `application/`, `adapters/`, `infra/`) con FastAPI y
  endpoint `/health`.
- CI en GitHub Actions (lint → tipos → tests → build de la imagen Docker), Dependabot,
  plantillas de issue y PR y workflow de release por tag.
- Dockerfile multi-stage no-root y `docker-compose.yml` con PostgreSQL 16.
- ADR 0001: fuentes legítimas y clic de postular humano.
