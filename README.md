# ApplyOps — búsqueda de trabajo continua, dirigida y con el clic final humano

[![CI](https://github.com/NicolasAndresCL/ApplyOps/actions/workflows/ci.yml/badge.svg)](https://github.com/NicolasAndresCL/ApplyOps/actions/workflows/ci.yml)
![Versión](https://img.shields.io/badge/versi%C3%B3n-0.4.0-blue)
![Python](https://img.shields.io/badge/python-3.14-3776AB)

| | |
|---|---|
| **Versión** | 0.4.0 |
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
- **Interfaz:** NiceGUI 4 consumiendo la API por HTTP, con los temas de Jaime (Luffy, Zoro y Eren) y el Cian del portafolio.
- **Todo dockerizado:** imagen multi-stage no-root y Docker Compose (UI + API + PostgreSQL).

**Fuente de verdad:** la tabla `ofertas` en PostgreSQL. Los criterios de búsqueda viven en
`perfil/busqueda.yaml`.

| Hito | Entrega | Estado |
|---|---|---|
| 0 | Esqueleto, CI, Docker | ✅ 0.1.0 |
| 1 | Recolección Get on Board + scoring + API | ✅ 0.2.0 |
| 2 | UI NiceGUI: bandeja priorizada, detalle con desglose, carga manual (LinkedIn, Indeed…) y temas | ✅ 0.3.0 |
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
│   │   ├── registrar_manual.py  # oferta copiada a mano; clave = hash de la URL sin rastreo
│   │   └── consultar.py         # bandeja priorizada y detalle
│   ├── adapters/
│   │   ├── inbound/api/         # routers FastAPI, esquemas (contrato), errores, correlation id
│   │   ├── inbound/ui/          # NiceGUI: otro proceso, habla con la API por HTTP
│   │   │   ├── cliente.py       # httpx asíncrono con timeout y errores tipados
│   │   │   ├── vistas.py        # bandeja, detalle, carga manual y ajustes (ui.sub_pages)
│   │   │   ├── temas/           # paletas y pieles: Jaime (Mugiwara, Gear 5, Zoro, Eren) + Cian (portafolio)
│   │   │   └── main.py          # composition root de la UI
│   │   └── outbound/
│   │       ├── getonboard.py        # adaptador Get on Board (contrato verificado con fixtures reales)
│   │       ├── http_resiliente.py   # timeout, reintento con backoff + jitter, errores tipados
│   │       ├── repo_sqlalchemy.py   # repositorio idempotente
│   │       └── perfil_yaml.py       # carga y valida perfil/busqueda.yaml con Pydantic
│   ├── infra/                   # settings, logs JSON, motor de BD, recolección programada
│   └── main.py                  # composition root: único lugar que conoce las clases concretas
├── migrations/                  # Alembic; la URL sale de DATABASE_URL, nunca del .ini
├── perfil/                      # busqueda.example.yaml versionado; el real no se versiona
├── assets/temas/                # imágenes de los personajes: NO versionadas (derechos de autor)
├── scripts/                     # ci_local.ps1 (clon del CI) · importar_temas_jaime.ps1
├── tests/{unit,integration,ui}  # ui: NiceGUI simulado contra la API real sobre fakes
├── docs/adr/                    # 0001 fuentes legítimas y clic humano · 0002 scoring explicable
├── docs/runbooks/               # fuente-sin-datos
├── Dockerfile                   # multi-stage, no-root, HEALTHCHECK a /health
└── docker-compose.yml           # api + PostgreSQL 16 con healthcheck; migra al arrancar
```

**Flujo:** `fuente (API pública) → adaptador → RecolectarOfertas → puntuar() → RepoOfertas → PostgreSQL`
y `navegador → UI (NiceGUI) → HTTP → router → caso de uso → RepoOfertas`. El dominio no conoce a nadie;
la UI no importa casos de uso, y los adaptadores no se hablan entre sí.

## Levantar con Docker

```bash
cp .env.example .env    # y cambiar POSTGRES_PASSWORD (y UI_STORAGE_SECRET para recordar el tema)
cp perfil/busqueda.example.yaml perfil/busqueda.yaml    # y ajustar tus criterios
./scripts/importar_temas_jaime.ps1                      # opcional: imágenes de los temas desde Jaime
docker compose up -d --build --wait
```

Abre <http://127.0.0.1:8080> y pulsa **Recolectar ahora**. El contenedor de la API aplica
`alembic upgrade head` antes de arrancar.

| Servicio | URL |
|---|---|
| UI | <http://127.0.0.1:8080> |
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
uvicorn applyops.main:crear_app --factory --reload       # API en :8000
python -m applyops.adapters.inbound.ui.main               # UI en :8080 (otra terminal)
```

## Endpoints

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/health` | Vivo: responde sin tocar dependencias. |
| GET | `/ready` | Listo: 200 si la base responde, 503 si no. |
| GET | `/ofertas` | Bandeja priorizada. Query: `min_puntaje` (0–100), `incluir_descartadas`, `incluir_vencidas`, `idioma` (`es`, `en`, `pt` o `no_indica`), `limite` (1–500). |
| GET | `/ofertas/{clave}` | Detalle con descripción y desglose del puntaje. |
| POST | `/ofertas` | Carga a mano una oferta (LinkedIn, Indeed…); 201 con la oferta puntuada. La misma URL actualiza. |
| POST | `/recolecciones` | Recolecta de todas las fuentes y devuelve el resumen por fuente. |

Todo error tiene la misma forma; el cliente distingue por `codigo`:

```json
{"error": {"codigo": "oferta_no_encontrada", "mensaje": "No existe la oferta 'getonboard:xyz'"}}
```

| Código | HTTP | Cuándo |
|---|---|---|
| `oferta_no_encontrada` | 404 | La clave no existe. |
| `recoleccion_en_curso` | 409 | Ya hay una recolección corriendo (manual o programada). |
| `entrada_invalida` | 422 | El cuerpo no cumple el esquema (URL mal formada, campo faltante…). |
| `oferta_invalida` | 422 | Los datos violan una regla de la oferta (sueldo mínimo mayor que el máximo). |
| `ruta_no_encontrada` / `metodo_no_permitido` | 404 / 405 | La ruta o el método no existen. |
| `error_interno` | 500 | Bug: el detalle va al log, nunca a la respuesta. |

Cada respuesta trae `X-Correlation-ID` (se respeta el que envíe el cliente) y los logs JSON lo incluyen.

## La interfaz

- **Bandeja:** ofertas de mayor a menor puntaje, con color por tramo (≥ 75 alto, ≥ 50 medio), filtro de
  puntaje mínimo, **idioma que pide la oferta** (Get on Board no lo publica en ~6 de cada 10: esas salen con
  «No indica»), «Ver descartadas» (con su motivo) y **Recolectar ahora**.
- **Detalle:** datos de la oferta, **por qué tiene ese puntaje** (una barra por componente con su
  explicación) y **Abrir la oferta para postular**, que lleva al portal: el clic final es tuyo.
- **Cargar oferta:** formulario para ofertas de portales sin API; la API la puntúa igual que a las
  recolectadas.
- **Ajustes:** elegir tema (se recuerda por navegador) y ver el estado de la API y de la base.
- **Temas** copiados de Jaime: 🏴‍☠️ Mugiwara y 🌞 Gear 5 (Luffy), ⚔️ Esmeralda (Zoro) y ⚡ Shingeki (Eren,
  por defecto). Las figuras y emblemas tienen derechos de autor y **no se versionan**:
  `scripts/importar_temas_jaime.ps1` los copia desde tu Jaime local a `assets/temas/`. Sin ellos, cada tema
  se ve con su paleta.
- **💠 Cian**, la identidad del portafolio: fondo aurora (cian, índigo y magenta), degradado de marca en
  títulos y menú, y glow en las tarjetas. Es CSS puro: se ve completo sin importar imágenes.
- **Si la API cae**, cada vista muestra el error con **Reintentar** en vez de romperse.

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

**Vencimiento:** cuando una fuente responde completa, sus ofertas guardadas que ya no aparecen se marcan
vencidas y salen de la bandeja (probablemente se cerraron); si reaparecen, vuelven. Con una respuesta
parcial —una consulta caída, corte por el tope de páginas u ofertas omitidas— no se vence nada, y las
ofertas cargadas a mano nunca vencen.

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
| `LOG_LEVEL` | api, ui | `INFO` | Nivel de logs. |
| `API_URL` | ui | `http://127.0.0.1:8000` (Compose: `http://api:8000`) | Dónde está la API. |
| `UI_HOST` / `UI_PUERTO` | ui | `127.0.0.1` / `8080` | Dónde escucha la UI. |
| `UI_STORAGE_SECRET` | ui | se genera uno por proceso | Firma la sesión donde se guarda el tema; fijarlo (≥ 16 caracteres) para que sobreviva a reinicios. |
| `TEMAS_ASSETS_DIR` | ui | `assets/temas` | Imágenes de los temas; si no existe, solo colores. |
| `DB_PUERTO_HOST` / `API_PUERTO_HOST` / `UI_PUERTO_HOST` | compose | `5433` / `8000` / `8080` | Puertos publicados en `127.0.0.1`. |

## Verificación

`scripts\ci_local.ps1 [-ConDocker]` clona HEAD en una carpeta temporal y reproduce el CI en un venv
nuevo con Python 3.14 (el runner solo ve lo versionado):

1. `ruff check` y `ruff format --check`.
2. `mypy` estricto (con el plugin de Pydantic).
3. `pytest` con cobertura mínima del **80 %**: hoy **212 tests, 98,5 %**, en ~14 s. En CI los de
   integración corren contra **PostgreSQL 16** (`DATABASE_URL_TEST`); en local, contra SQLite si no está
   definida. El esquema de prueba se crea **con las migraciones**, y un test compara modelos y
   migraciones. Los de la UI usan el `User` simulado de NiceGUI hablando por `httpx.ASGITransport` con la
   **API real** montada sobre fakes: prueban el contrato UI → HTTP → API sin red.
4. Con `-ConDocker`: `docker compose up --wait` en un proyecto y puertos propios (UI incluida),
   `/health` en 200, la UI responde y `down -v`.

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
- **Degradar en vez de fallar.** Una consulta caída se informa en el resumen y en el log, se guarda
  lo que sí respondió y el ciclo sigue con las demás fuentes ([runbook](docs/runbooks/fuente-sin-datos.md)).
- **La UI es un cliente más de la API.** Corre en otro proceso y solo habla HTTP: el mismo backend
  sirve a n8n o a otro front, y la UI se puede reemplazar sin tocar el dominio.
- **Las imágenes con derechos de autor no entran al repo.** Los temas versionan sus colores y su CSS;
  las figuras se importan en local y, si faltan, el tema degrada a su paleta.
- **Hexagonal desde el día uno.** Cada fuente es un adaptador detrás del mismo puerto: agregar una no
  toca el scoring ni la API, y los casos de uso se testean con fakes, sin red.

## Autor

**Nicolás Andrés Cano Leal**\
Backend Engineer → SRE | Python · Django · Kubernetes · Terraform · CI/CD

- LinkedIn: [linkedin.com/in/nicolasandrescl](https://www.linkedin.com/in/nicolasandrescl/)
- Portafolio: [nicolasandrescl.github.io](https://nicolasandrescl.github.io/)
- Correo: [nicolas.cano.leal@gmail.com](mailto:nicolas.cano.leal@gmail.com)

ApplyOps v0.4.0 · 25 de noviembre de 2026
