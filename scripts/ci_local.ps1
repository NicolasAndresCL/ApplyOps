<#
.SYNOPSIS
    Reproduce el CI de GitHub Actions sobre un clon limpio de HEAD.

.DESCRIPTION
    El runner solo ve lo versionado: por eso se clona HEAD en una carpeta
    temporal (no se usa el working copy) y se instala en un venv nuevo con
    Python 3.14, la misma versión del workflow. Corre los jobs en el mismo
    orden: lint -> formato -> tipos -> tests con cobertura -> (opcional) stack Docker.

    Para que los tests de integración corran contra PostgreSQL como en CI,
    definir antes DATABASE_URL_TEST; sin ella usan SQLite en memoria.

.PARAMETER ConDocker
    Además levanta el stack con docker compose, verifica /health y lo baja.

.EXAMPLE
    .\scripts\ci_local.ps1 -ConDocker

    Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
#>
param([switch]$ConDocker)

# 'Continue' y no 'Stop': en PowerShell 5.1 cualquier línea que un comando nativo
# (docker, git) escriba en stderr se vuelve error terminante con 'Stop', aunque
# salga con código 0. El éxito de cada paso se mide con $LASTEXITCODE.
$ErrorActionPreference = 'Continue'
$repo = (git rev-parse --show-toplevel)
$destino = Join-Path ([IO.Path]::GetTempPath()) ("applyops-ci-" + [guid]::NewGuid().ToString('N').Substring(0, 8))
$fallos = 0

function Invoke-Paso([string]$nombre, [scriptblock]$bloque) {
    Write-Host "`n=== $nombre ===" -ForegroundColor Cyan
    & $bloque
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  X $nombre fallo (exit $LASTEXITCODE)" -ForegroundColor Red
        $script:fallos++
    } else {
        Write-Host "  OK $nombre" -ForegroundColor Green
    }
}

try {
    git clone --quiet $repo $destino
    Push-Location $destino
    py -3.14 -m venv .venv
    $py = Join-Path $destino '.venv\Scripts\python.exe'
    & $py -m pip install --quiet --disable-pip-version-check -e ".[dev]"
    if ($LASTEXITCODE -ne 0) { throw 'pip install fallo' }

    # Mismos entrypoints que el workflow (ruff, mypy, pytest), no "python -m".
    $bin = Join-Path $destino '.venv\Scripts'
    Invoke-Paso 'ruff check'      { & "$bin\ruff.exe" check . }
    Invoke-Paso 'ruff format'     { & "$bin\ruff.exe" format --check . }
    Invoke-Paso 'mypy'            { & "$bin\mypy.exe" }
    Invoke-Paso 'pytest + cov'    { & "$bin\pytest.exe" -rs --cov --cov-report=term-missing --cov-fail-under=80 }

    if ($ConDocker) {
        $env:POSTGRES_PASSWORD = 'ci-local-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
        # Proyecto y puertos propios: no pisa el stack de desarrollo si está arriba.
        $env:COMPOSE_PROJECT_NAME = 'applyops-ci-local'
        $env:DB_PUERTO_HOST = '5443'
        $env:API_PUERTO_HOST = '8010'
        $env:UI_PUERTO_HOST = '8020'
        try {
            Invoke-Paso 'docker compose up --wait' { docker compose up -d --build --wait --wait-timeout 180 }
            Invoke-Paso '/health'                  { curl.exe --fail --silent --show-error http://127.0.0.1:8010/health }
            Invoke-Paso 'UI responde'              { curl.exe --fail --silent --show-error --output NUL http://127.0.0.1:8020/ajustes }
        } finally {
            docker compose down -v 2>&1 | Out-Null
        }
    }
} finally {
    Pop-Location -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force $destino -ErrorAction SilentlyContinue
}

if ($fallos -eq 0) { Write-Host "`nTodo en verde." -ForegroundColor Green; exit 0 }
Write-Host "`n$fallos paso(s) en rojo: NO pushees todavia." -ForegroundColor Red
exit 1
