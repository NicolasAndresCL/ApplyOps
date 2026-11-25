# syntax=docker/dockerfile:1

# --- Etapa 1: construir el venv con las dependencias -------------------------
FROM python:3.14-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Primero solo lo necesario para instalar: la capa se reutiliza mientras no
# cambien las dependencias.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install .

# --- Etapa 2: imagen final, sin compiladores ni caché de pip -----------------
FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN groupadd --system app && useradd --system --gid app --home-dir /app app
WORKDIR /app
# La UI (NiceGUI) guarda sesiones en /app/.nicegui: el usuario no-root necesita escribir ahí.
RUN mkdir -p /app/.nicegui && chown app:app /app/.nicegui

COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app alembic.ini ./
COPY --chown=app:app migrations ./migrations
COPY --chown=app:app perfil ./perfil
COPY --chown=app:app docker-entrypoint.sh ./

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"]

ENTRYPOINT ["sh", "./docker-entrypoint.sh"]
