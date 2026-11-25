# ApplyOps — búsqueda de trabajo continua, dirigida y con el clic final humano

[![CI](https://github.com/NicolasAndresCL/ApplyOps/actions/workflows/ci.yml/badge.svg)](https://github.com/NicolasAndresCL/ApplyOps/actions/workflows/ci.yml)
![Versión](https://img.shields.io/badge/versi%C3%B3n-0.2.0-blue)
![Python](https://img.shields.io/badge/python-3.14-3776AB)

| | |
|---|---|
| **Versión** | 0.2.0 |
| **Fecha** | 25 de noviembre de 2026 |
| **Autor** | [Nicolás Andrés Cano Leal](#autor) |

ApplyOps automatiza **lo que conviene automatizar** de una búsqueda de trabajo: **recolectar ofertas**
de fuentes con API pública, **puntuarlas contra el perfil** (stack, sueldo, modalidad, seniority,
idioma) con un desglose que explica cada punto, **generar CV y carta adaptados** a cada una y **llevar
el seguimiento** (postulada, entrevista, respuesta). Lo que **no** hace es postular: el clic final
siempre lo da una persona ([ADR 0001](docs/adr/0001-fuentes-legitimas-y-clic-humano.md)).

- **Backend:** FastAPI, arquitectura hexagonal (dominio puro, puertos y adaptadores).
- **Persistencia:** PostgreSQL 16 con SQLAlchemy 2 y migraciones Alembic.
- **Fuentes:** Get on Board (API pública). Remotive, RemoteOK, Himalayas, We Work Remotely, Torre.ai y
  los ATS públicos de Greenhouse, Lever y Ashby en el hito 5.
- **Interfaz:** NiceGUI consumiendo la API por HTTP (hito 2).
- **Todo dockerizado:** imagen multi-stage no-root y Docker Compose.

**Fuente de verdad:** la tabla `ofertas` en PostgreSQL. Los criterios de búsqueda viven en
`perfil/busqueda.yaml`.

| Hito | Entrega | Estado |
|---|---|---|
| 0 | Esqueleto, CI, Docker | ✅ 0.1.0 |
| 1 | Recolección Get on Board + scoring + API | ✅ 0.2.0 |
| 2 | UI NiceGUI: bandeja priorizada y carga manual de ofertas (LinkedIn, Indeed…) | ⏳ |
| 3 | CV y carta adaptados (plantilla + Claude, sin inventar hechos) → PDF | ⏳ |
| 4 | Seguimiento: estados, historial, recordatorios, resumen semanal | ⏳ |
| 5 | Más fuentes y ATS de empresas objetivo, circuit breaker, métricas | ⏳ |
| 6 | Despliegue en el VPS (Traefik, backups, aviso diario por Telegram vía n8n) | ⏳ |

## Arquitectura

```
ApplyOps/
├── src/applyops/
│   ├── domain/                  # núcleo puro: no importa FastAPI, httpx ni SQLAlchemy
│   │   ├── oferta.py            # Oferta normalizada + invariantes; clave natural fuente:id
│   │   ├── perfil.py            # criterios de búsqueda y pesos (deben sumar 100)
│   │   ├── scoring.py           # puntuar(): función pura, desglose explicable
│   │   ├── puertos.py           # Protocol: FuenteOfertas, RepoOfertas
│   │   └── errores.py           # errores tipados; cada uno con su `codigo`
│   ├── application/
│   │   ├── recolectar.py        # recorre fuentes, deduplica, puntúa y guarda; degrada por fuente
│   │   └── consultar.py         # bandeja priorizada y detalle
│   ├── adapters/
│   │   ├── inbound/api/         # routers FastAPI, esquemas (contrato), errores, correlation id
│   │   └── outbound/
│   │       ├── getonboard.py        # adaptador Get on Board (contrato verificado con fixtures reales)
│   │       ├── http_resiliente.py   # timeout, reintento con backoff + jitter, errores tipados
│   │       ├── repo_sqlalchemy.py   # repositorio idempotente
│   │       └── perfil_yaml.py       # carga y valida perfil/busqueda.yaml con Pydantic
│   ├── infra/                   # settings, logs JSON, motor de BD, recolección programada
│   └── main.py                  # composition root: único lugar que conoce las clases concretas
├── migrations/                  # Alembic; la URL sale de DATABASE_URL, nunca del .ini
├── perfil/                      # busqueda.example.yaml versionado; el real no se versiona
├── tests/{unit,integration}     # unit sin red ni BD (fakes); integración contra SQLite o PostgreSQL
├── docs/adr/                    # 0001 fuentes legítimas y clic humano · 0002 scoring explicable
├── docs/runbooks/               # fuente-sin-datos
├── Dockerfile                   # multi-stage, no-root, HEALTHCHECK a /health
└── docker-compose.yml           # api + PostgreSQL 16 con healthcheck; migra al arrancar
```

**Flujo:** `fuente (API pública) → adaptador → RecolectarOfertas → puntuar() → RepoOfertas → PostgreSQL`
y `cliente → router → ConsultarOfertas → RepoOfertas`. El dominio no conoce a nadie; los adaptadores no
se hablan entre sí.

## Levantar con Docker

```bash
cp .env.example .env    # y cambiar POSTGRES_PASSWORD
cp perfil/busqueda.example.yaml perfil/busqueda.yaml    # y ajustar tus criterios
docker compose up -d --build --wait
curl -X POST http://127.0.0.1:8000/recolecciones        # primera recolección
```

El contenedor aplica `alembic upgrade head` antes de arrancar la API.

| Servicio | URL |
|---|---|
| API | <http://127.0.0.1:8000> |
| OpenAPI | <http://127.0.0.1:8000/docs> |
| PostgreSQL | `127.0.0.1:5433` (solo local; 5433 para no chocar con un PostgreSQL local) |

`docker compose down` baja el stack y **conserva** la base de datos; `docker compose down -v`
**la borra**.

## Correr en local sin Docker

Requiere **Python 3.14** y un PostgreSQL (o SQLite para probar: `sqlite+pysqlite:///applyops.db`).

```powershell
py -3.14 -m venv env
env\Scripts\activate
pip install -e ".[dev]"
$env:DATABASE_URL = "postgresql+psycopg://applyops:<clave>@localhost:5433/applyops"
alembic upgrade head
uvicorn applyops.main:crear_app --factory --reload
```

## Endpoints

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/health` | Vivo: responde sin tocar dependencias. |
| GET | `/ready` | Listo: 200 si la base responde, 503 si no. |
| GET | `/ofertas` | Bandeja priorizada. Query: `min_puntaje` (0–100), `incluir_descartadas`, `limite` (1–500). |
| GET | `/ofertas/{clave}` | Detalle con descripción y desglose del puntaje. |
| POST | `/recolecciones` | Recolecta de todas las fuentes y devuelve el resumen por fuente. |

Todo error tiene la misma forma; el cliente distingue por `codigo`:

```json
{"error": {"codigo": "oferta_no_encontrada", "mensaje": "No existe la oferta 'getonboard:xyz'"}}
```

| Código | HTTP | Cuándo |
|---|---|---|
| `oferta_no_encontrada` | 404 | La clave no existe. |
| `recoleccion_en_curso` | 409 | Ya hay una recolección corriendo (manual o programada). |
| `error_interno` | 500 | Bug: el detalle va al log, nunca a la respuesta. |

Cada respuesta trae `X-Correlation-ID` (se respeta el que envíe el cliente) y los logs JSON lo incluyen.

## Cómo se puntúa

| Componente | Máximo | Regla |
|---|---|---|
| Stack | 50 | Suma de pesos (1–3) de las skills mencionadas, saturada en `saturacion_stack`. Palabra completa, sin tildes, con sinónimos. |
| Modalidad | 20 | Factor por modalidad (remoto, remoto local, híbrido, presencial). |
| Sueldo | 15 | Rango en USD contra tu mínimo; si cruza el mínimo, vale la parte que lo supera. |
| Seniority | 10 | Factor por nivel pedido. |
| Idioma | 5 | Completo si está en tus idiomas o no se especifica. |

Un dato **no publicado** (sueldo, seniority, modalidad) recibe la **mitad** del componente: el 58 % de las
ofertas de Get on Board no publica sueldo. Se **descarta** (total 0, con motivo y desglose) la oferta con
una palabra excluida en el título, o híbrida/presencial/remota-local fuera de `paises_presenciales`.

## Variables de entorno

| Variable | Servicio | Por defecto | Para qué |
|---|---|---|---|
| **`POSTGRES_PASSWORD`** | db, api | — | Clave de PostgreSQL en Docker Compose. |
| **`DATABASE_URL`** | api | — (Compose la arma) | URL SQLAlchemy (`postgresql+psycopg://…`). |
| `PERFIL_BUSQUEDA_PATH` | api | `perfil/busqueda.yaml` | Criterios de scoring; si no existe, usa el ejemplo y lo avisa. |
| `RECOLECCION_INTERVALO_HORAS` | api | `0` | Cada cuántas horas recolectar sola; `0` = solo manual. |
| `HTTP_TIMEOUT_SEGUNDOS` | api | `15` | Timeout de cada llamada a una fuente. |
| `HTTP_REINTENTOS` | api | `3` | Intentos ante 429/5xx/red (1–6). |
| `GETONBOARD_URL_BASE` | api | `https://www.getonbrd.com/api/v0` | Base de la API de Get on Board. |
| `GETONBOARD_MAX_PAGINAS` | api | `4` | Páginas de 50 por consulta. |
| `LOG_LEVEL` | api | `INFO` | Nivel de logs. |
| `DB_PUERTO_HOST` / `API_PUERTO_HOST` | compose | `5433` / `8000` | Puertos publicados en `127.0.0.1`. |

## Verificación

`scripts\ci_local.ps1 [-ConDocker]` clona HEAD en una carpeta temporal y reproduce el CI en un venv
nuevo con Python 3.14 (el runner solo ve lo versionado):

1. `ruff check` y `ruff format --check`.
2. `mypy` estricto (con el plugin de Pydantic).
3. `pytest` con cobertura mínima del **80 %**: hoy **112 tests, 99,6 %**, en ~8 s. En CI los de
   integración corren contra **PostgreSQL 16** (`DATABASE_URL_TEST`); en local, contra SQLite si no está
   definida. El esquema de prueba se crea **con las migraciones**, y un test compara modelos y
   migraciones.
4. Con `-ConDocker`: `docker compose up --wait` en un proyecto y puertos propios, `/health` en 200 y
   `down -v`.

Prueba punta a punta del 2026-11-25 contra la API real: **239 ofertas** recolectadas en ~7 s, segunda
corrida con **0 nuevas** (idempotente).

## Decisiones de diseño

- **El clic de postular es humano.** Automatizar la postulación viola los términos de LinkedIn e
  Indeed y rinde menos que 5–10 postulaciones dirigidas por semana. ApplyOps prioriza y prepara.
- **Solo fuentes con API o feed público.** Los portales sin API se cargarán a mano (hito 2) y se
  puntúan igual.
- **Scoring determinista y explicable, sin LLM** ([ADR 0002](docs/adr/0002-scoring-explicable.md)):
  reproducible, gratis de recalcular y con el porqué de cada punto. El LLM queda para redactar.
- **Lo desconocido no es cero.** Penalizar a cero el sueldo no publicado hundiría a más de la mitad de
  las ofertas por falta de dato, no por ser malas.
- **Contract tests con respuestas reales.** Capturar el payload real destapó que Get on Board pone
  `"Remote"` en `countries`; leído como país, descartaba 62 de 239 ofertas.
- **Toda salida a la red tiene timeout**, también la conexión a PostgreSQL: sin `connect_timeout`,
  `/ready` tardaba 130 s con la base caída en vez de responder 503.
- **Degradar en vez de fallar.** Una fuente caída se informa en el resumen y en el log, y el ciclo
  sigue con las demás ([runbook](docs/runbooks/fuente-sin-datos.md)).
- **Hexagonal desde el día uno.** Cada fuente es un adaptador detrás del mismo puerto: agregar una no
  toca el scoring ni la API, y los casos de uso se testean con fakes, sin red.

## Autor

**Nicolás Andrés Cano Leal**\
Backend Engineer → SRE | Python · Django · Kubernetes · Terraform · CI/CD

- LinkedIn: [linkedin.com/in/nicolasandrescl](https://www.linkedin.com/in/nicolasandrescl/)
- Portafolio: [nicolasandrescl.github.io](https://nicolasandrescl.github.io/)
- Correo: [nicolas.cano.leal@gmail.com](mailto:nicolas.cano.leal@gmail.com)

ApplyOps v0.2.0 · 25 de noviembre de 2026
