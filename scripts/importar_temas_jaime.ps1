<#
.SYNOPSIS
    Copia desde Jaime las imágenes y fuentes de los temas Luffy, Zoro y Eren.

.DESCRIPTION
    Las figuras de los personajes y sus emblemas tienen derechos de autor: no se
    versionan en ApplyOps (repo público). Este script los copia, solo en tu equipo,
    a assets/temas/ (en .gitignore), con la misma estructura de carpetas que usa
    Jaime (op/ y equipo/). Sin ellos, los temas se ven con sus colores planos.

    Es idempotente: volver a correrlo sobrescribe con la versión actual de Jaime.

.PARAMETER Jaime
    Raíz del repo de Jaime. Por defecto, C:\dev\projects\Automatizacion_LiveOps3.0.

.EXAMPLE
    .\scripts\importar_temas_jaime.ps1

    Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
#>
param([string]$Jaime = 'C:\dev\projects\Automatizacion_LiveOps3.0')

$ErrorActionPreference = 'Stop'
$origen = Join-Path $Jaime 'assets\themes'
$destino = Join-Path (Split-Path $PSScriptRoot -Parent) 'assets\temas'

# Solo lo que usan los cuatro temas de ApplyOps (nada de PedidosYa ni de otros temas).
$archivos = @(
    'op\figuras\mugiwara.png', 'op\figuras\luffy_g5.png', 'op\figuras\esmeralda.png',
    'op\rogers\zoro.png', 'op\mugiwara\skull.png', 'op\mugiwara\bg.jpg',
    'op\tex\madera.png', 'op\tex\haki1.png', 'op\tex\haki2.png',
    'op\fuentes\pirata-one.woff2', 'op\fuentes\cinzel.woff2',
    'equipo\figuras\eren.png', 'equipo\emblemas\eren.png', 'equipo\fondos\eren.jpg',
    'equipo\tex\muro.png'
)

if (-not (Test-Path $origen)) {
    Write-Host "No encuentro $origen. Indica la ruta de Jaime con -Jaime <ruta>." -ForegroundColor Red
    exit 1
}

$copiados = 0
$faltan = @()
foreach ($rel in $archivos) {
    $src = Join-Path $origen $rel
    if (-not (Test-Path $src)) { $faltan += $rel; continue }
    $dst = Join-Path $destino $rel
    New-Item -ItemType Directory -Force (Split-Path $dst -Parent) | Out-Null
    Copy-Item $src $dst -Force
    $copiados++
}

Write-Host "Copiados $copiados de $($archivos.Count) archivos a $destino" -ForegroundColor Green
if ($faltan.Count -gt 0) {
    Write-Host "No estaban en Jaime (esas capas del tema quedan sin imagen):" -ForegroundColor Yellow
    $faltan | ForEach-Object { Write-Host "  $_" }
}
