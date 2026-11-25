# ApplyOps — búsqueda de trabajo continua, dirigida y con el clic final humano

[![CI](https://github.com/NicolasAndresCL/ApplyOps/actions/workflows/ci.yml/badge.svg)](https://github.com/NicolasAndresCL/ApplyOps/actions/workflows/ci.yml)
![Versión](https://img.shields.io/badge/versi%C3%B3n-0.1.0-blue)
![Python](https://img.shields.io/badge/python-3.14-3776AB)

| | |
|---|---|
| **Versión** | 0.1.0 |
| **Fecha** | 25 de noviembre de 2026 |
| **Autor** | [Nicolás Andrés Cano Leal](#autor) |

ApplyOps automatiza **lo que conviene automatizar** de una búsqueda de trabajo: **recolectar ofertas**
de fuentes con API pública, **puntuarlas contra el perfil** (stack, sueldo, modalidad), **generar CV y
carta adaptados** a cada una y **llevar el seguimiento** (postulada, entrevista, respuesta). Lo que
**no** hace es postular: el clic final siempre lo da una persona. Ver
[ADR 0001](docs/adr/0001-fuentes-legitimas-y-clic-humano.md).

- **Backend:** FastAPI, arquitectura hexagonal (dominio puro, puertos y adaptadores).
- **Persistencia:** PostgreSQL 16 con SQLAlchemy 2 y migraciones Alembic.
- **Interfaz:** NiceGUI consumiendo la API por HTTP (hito 2).
- **Todo dockerizado:** imagen multi-stage no-root y Docker Compose.

> Estado: **0.1.0 — esqueleto con CI**. La hoja de ruta por hitos está en el [CHANGELOG](CHANGELOG.md).

## Arquitectura

```
ApplyOps/
├── src/applyops/
│   ├── domain/              # entidades y reglas puras; no importa nada de afuera
│   ├── application/         # casos de uso; dependen solo de puertos del dominio
│   ├── adapters/
│   │   ├── inbound/api/     # routers FastAPI: validan, llaman al caso de uso, traducen a HTTP
│   │   └── outbound/        # clientes de fuentes de ofertas, repositorio SQLAlchemy
│   ├── infra/               # settings, logging, base de datos
│   └── main.py              # composition root: único lugar que conoce las clases concretas
├── migrations/              # Alembic; la URL sale de DATABASE_URL, nunca del .ini
├── perfil/                  # criterios de búsqueda (el real no se versiona)
├── tests/{unit,integration} # unit sin red ni BD; integración contra SQLite o PostgreSQL
├── docs/{adr,runbooks}/     # decisiones de arquitectura y runbooks de alertas
├── Dockerfile               # multi-stage, no-root, HEALTHCHECK a /health
└── docker-compose.yml       # api + PostgreSQL 16 con healthcheck
```

**Flujo:** `fuente (API pública) → adaptador → caso de uso → dominio (scoring) → repositorio → API`.
El dominio no conoce FastAPI, httpx ni SQLAlchemy.

## Levantar con Docker

```bash
cp .env.example .env    # y cambiar POSTGRES_PASSWORD
docker compose up -d --build --wait
```

| Servicio | URL |
|---|---|
| API | <http://127.0.0.1:8000> |
| OpenAPI | <http://127.0.0.1:8000/docs> |
| PostgreSQL | `127.0.0.1:5432` (solo local) |

`docker compose down` baja el stack y **conserva** la base de datos; `docker compose down -v`
**la borra**.

## Correr en local sin Docker

Requiere **Python 3.14**.

```powershell
py -3.14 -m venv env
env\Scripts\activate
pip install -e ".[dev]"
uvicorn applyops.main:app --reload
```

## Endpoints

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/health` | Vivo: responde sin tocar dependencias. |

## Variables de entorno

| Variable | Servicio | Por defecto | Para qué |
|---|---|---|---|
| **`POSTGRES_PASSWORD`** | db, api | — | Clave de PostgreSQL en Docker Compose. |
| `DATABASE_URL` | api | — | URL SQLAlchemy (`postgresql+psycopg://…`). |
| `LOG_LEVEL` | api | `INFO` | Nivel de logs. |

## Verificación

`scripts\ci_local.ps1 [-ConDocker]` clona HEAD en una carpeta temporal y reproduce el CI en un venv
nuevo con Python 3.14:

1. `ruff check` y `ruff format --check`.
2. `mypy` en modo estricto.
3. `pytest` con cobertura mínima del **80 %** (en CI, contra PostgreSQL 16).
4. Con `-ConDocker`: `docker compose up --wait`, `/health` en 200 y `down -v`.

## Decisiones de diseño

- **El clic de postular es humano.** Automatizar la postulación viola los términos de LinkedIn e
  Indeed y rinde menos que 5–10 postulaciones dirigidas por semana. ApplyOps prioriza y prepara;
  la persona decide.
- **Solo fuentes con API o feed público.** Los portales sin API se cargan a mano y se puntúan igual.
- **Hexagonal desde el día uno.** Cada fuente es un adaptador detrás del mismo puerto: agregar una
  no toca el scoring ni la API, y los casos de uso se testean con fakes, sin red.
- **CI que arranca el servicio**, no solo lint: el job de build levanta el stack completo y le pega
  a `/health`.

## Autor

**Nicolás Andrés Cano Leal**\
Backend Engineer → SRE | Python · Django · Kubernetes · Terraform · CI/CD

- LinkedIn: [linkedin.com/in/nicolasandrescl](https://www.linkedin.com/in/nicolasandrescl/)
- Portafolio: [nicolasandrescl.github.io](https://nicolasandrescl.github.io/)
- Correo: [nicolas.cano.leal@gmail.com](mailto:nicolas.cano.leal@gmail.com)

ApplyOps v0.1.0 · 25 de noviembre de 2026
