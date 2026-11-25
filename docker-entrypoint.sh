#!/bin/sh
# Arranque del contenedor: aplica migraciones pendientes y levanta la API.
# `exec` deja a uvicorn como PID 1, así recibe el SIGTERM de `docker stop`
# y cierra limpio en vez de morir a los 10 s.
set -eu

alembic upgrade head
exec uvicorn applyops.main:app --host 0.0.0.0 --port 8000 --proxy-headers
