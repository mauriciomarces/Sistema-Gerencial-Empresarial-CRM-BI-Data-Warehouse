# ========================================
# SCRIPT MAESTRO (Windows PowerShell)
# Sistema CRM + BI + Data Warehouse Nestlé
# Uso: .\start.ps1
# ========================================

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Write-Header($msg) {
    Write-Host "`n=========================================" -ForegroundColor Blue
    Write-Host $msg -ForegroundColor Blue
    Write-Host "=========================================" -ForegroundColor Blue
}

function Write-Ok($msg)   { Write-Host "✓ $msg" -ForegroundColor Green }
function Write-Err($msg)  { Write-Host "✗ $msg" -ForegroundColor Red; exit 1 }
function Write-Info($msg) { Write-Host "ℹ $msg" -ForegroundColor Yellow }

Write-Header "VALIDACIONES PREVIAS"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Err "Docker no está instalado. Instala Docker Desktop y reinicia."
}
Write-Ok "Docker instalado"

docker compose version *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Err "Docker Compose no disponible. Actualiza Docker Desktop."
}
Write-Ok "Docker Compose instalado"

Write-Header "CREANDO ESTRUCTURA DE DIRECTORIOS"
@("odoo/addons", "odoo/config", "sql/init", "etl/logs", "etl/scripts", "powerbi", "scripts/logs") | ForEach-Object {
    New-Item -ItemType Directory -Force -Path $_ | Out-Null
}
Write-Ok "Estructura de directorios creada"

Write-Header "CONFIGURANDO ARCHIVOS"
if (-not (Test-Path "sql/init/01_data_warehouse.sql")) {
    Copy-Item "sql/01_data_warehouse.sql" "sql/init/" -ErrorAction SilentlyContinue
}
if (-not (Test-Path "sql/init/02_datos_ejemplo.sql")) {
    Copy-Item "sql/02_datos_ejemplo.sql" "sql/init/" -ErrorAction SilentlyContinue
}
Write-Ok "Archivos configurados"

Write-Header "LIMPIEZA DE CONTENEDORES ANTERIORES"
docker compose down --volumes 2>$null
Write-Ok "Contenedores previos removidos"

Write-Header "INICIANDO SERVICIOS"
Write-Info "Construyendo imágenes Docker (puede tardar varios minutos la primera vez)..."
docker compose build
docker compose up -d
Write-Ok "Contenedores iniciados"

Write-Header "ESPERANDO A QUE LOS SERVICIOS ESTÉN LISTOS"

$timeout = 300
$elapsed = 0
while ($elapsed -lt $timeout) {
    docker compose exec -T sqlserver /opt/mssql-tools18/bin/sqlcmd -S localhost -C -U sa -P "NestleAdmin@2024" -Q "SELECT 1" 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { Write-Ok "SQL Server está listo"; break }
    Write-Host "Esperando SQL Server... ($elapsed/$timeout s)"
    Start-Sleep -Seconds 10
    $elapsed += 10
}

$elapsed = 0
while ($elapsed -lt $timeout) {
    docker compose exec -T postgres pg_isready -U odoo 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { Write-Ok "PostgreSQL está listo"; break }
    Write-Host "Esperando PostgreSQL... ($elapsed/$timeout s)"
    Start-Sleep -Seconds 10
    $elapsed += 10
}

$odooReady = docker compose exec -T -e PGPASSWORD=odoo postgres psql -U odoo -d odoo_production -tAc `
    "SELECT 1 FROM information_schema.tables WHERE table_name='ir_module_module' LIMIT 1" 2>$null
if ($odooReady -notmatch "1") {
    Write-Info "Instalando módulos base de Odoo (puede tardar varios minutos)..."
    docker compose stop odoo 2>$null
    docker compose run --rm odoo odoo --config=/etc/odoo/odoo.conf -d odoo_production -i base --stop-after-init --without-demo=all
    docker compose start odoo
    Write-Ok "Base de datos Odoo inicializada"
}

$elapsed = 0
while ($elapsed -lt $timeout) {
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:8069/web/login" -UseBasicParsing -TimeoutSec 5
        if ($r.StatusCode -in 200, 303) { Write-Ok "Odoo está listo"; break }
    } catch { }
    Write-Host "Esperando Odoo... ($elapsed/$timeout s)"
    Start-Sleep -Seconds 15
    $elapsed += 15
}

Write-Header "INICIALIZANDO DATA WAREHOUSE"
Write-Info "Creando base de datos nestle_dw..."
docker compose exec -T sqlserver /opt/mssql-tools18/bin/sqlcmd -S localhost -C -U sa -P "NestleAdmin@2024" -Q "CREATE DATABASE nestle_dw" 2>$null
Start-Sleep -Seconds 3
Write-Info "Ejecutando scripts SQL..."
docker compose exec -T sqlserver /opt/mssql-tools18/bin/sqlcmd -S localhost -C -U sa -P "NestleAdmin@2024" -i /docker-entrypoint-initdb.d/01_data_warehouse.sql
Start-Sleep -Seconds 3
Write-Info "Insertando datos de ejemplo..."
docker compose exec -T sqlserver /opt/mssql-tools18/bin/sqlcmd -S localhost -C -U sa -P "NestleAdmin@2024" -i /docker-entrypoint-initdb.d/02_datos_ejemplo.sql
Write-Ok "Data Warehouse inicializado"

Write-Info "Reiniciando Portainer..."
docker compose restart portainer | Out-Null
Start-Sleep -Seconds 5
Write-Ok "Portainer disponible en http://localhost:9000"

Write-Header "SISTEMA LISTO - INFORMACIÓN DE ACCESO"
Write-Host @"

WEB:
  Odoo ERP/CRM:     http://localhost:8069
  Portainer:        http://localhost:9000
  pgAdmin:          http://localhost:5050

CREDENCIALES:
  Odoo:             admin / admin
  SQL Server:       sa / NestleAdmin@2024  (BD: nestle_dw)
  PostgreSQL:       odoo / odoo            (BD: odoo_production)
  pgAdmin:          admin@nestle.com / PGAdmin@2024
  Portainer:        admin / admin12345678  (crear en primer acceso)

SIGUIENTES PASOS:
  1. Portainer → registrar admin (admin / admin12345678)
  2. Odoo → instalar Ventas, CRM, Inventario
  3. SSMS → 127.0.0.1,1433 → nestle_dw
  4. Power BI → ver README.md sección Power BI
  5. ETL manual: docker compose exec etl-service python etl_nestle.py

Documentación completa: README.md

"@ -ForegroundColor Cyan
