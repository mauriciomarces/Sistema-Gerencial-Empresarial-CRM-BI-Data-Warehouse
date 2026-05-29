#!/bin/bash
# ========================================
# SCRIPT MAESTRO - INICIA TODO EL SISTEMA
# Sistema CRM + BI + Data Warehouse Nestle
# ========================================

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ========================================
# FUNCIONES
# ========================================

print_header() {
    echo -e "${BLUE}"
    echo "========================================="
    echo "$1"
    echo "========================================="
    echo -e "${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# ========================================
# VALIDACIONES PREVIAS
# ========================================

print_header "VALIDACIONES PREVIAS"

# Verificar Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker no está instalado"
    exit 1
fi
print_success "Docker instalado"

# Verificar Docker Compose
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose no está instalado"
    exit 1
fi
print_success "Docker Compose instalado"

# Verificar espacio en disco (compatible Windows/Linux)
if df -k . > /dev/null 2>&1; then
    SPACE_AVAILABLE=$(df -k . | awk 'NR==2 {print $4}')
    SPACE_REQUIRED=10485760  # 10GB en KB
    if [ -n "$SPACE_AVAILABLE" ] && [ "$SPACE_AVAILABLE" -lt "$SPACE_REQUIRED" ] 2>/dev/null; then
        print_error "No hay suficiente espacio en disco (requiere 10GB)"
        exit 1
    fi
fi
print_success "Espacio en disco disponible"

# ========================================
# CREAR DIRECTORIOS
# ========================================

print_header "CREANDO ESTRUCTURA DE DIRECTORIOS"

mkdir -p odoo/addons
mkdir -p odoo/config
mkdir -p sql/init
mkdir -p etl/logs
mkdir -p etl/scripts
mkdir -p powerbi
mkdir -p scripts/logs

print_success "Estructura de directorios creada"

# ========================================
# COPIAR ARCHIVOS DE CONFIGURACIÓN
# ========================================

print_header "CONFIGURANDO ARCHIVOS"

# Copiar scripts SQL
if [ ! -f "sql/init/01_data_warehouse.sql" ]; then
    cp sql/01_data_warehouse.sql sql/init/ 2>/dev/null || true
fi

if [ ! -f "sql/init/02_datos_ejemplo.sql" ]; then
    cp sql/02_datos_ejemplo.sql sql/init/ 2>/dev/null || true
fi

print_success "Archivos configurados"

# ========================================
# LIMPIAR CONTENEDORES ANTERIORES
# ========================================

print_header "LIMPIEZA DE CONTENEDORES ANTERIORES"

docker-compose down --volumes 2>/dev/null || true
print_success "Contenedores previos removidos"

# ========================================
# CONSTRUIR E INICIAR SERVICIOS
# ========================================

print_header "INICIANDO SERVICIOS"

print_info "Construyendo imágenes Docker..."
docker-compose build --no-cache 2>&1 | grep -E "(Building|Successfully)" || true

print_info "Iniciando contenedores..."
docker-compose up -d

print_success "Contenedores iniciados"

# ========================================
# ESPERAR A QUE LOS SERVICIOS ESTÉN LISTOS
# ========================================

print_header "ESPERANDO A QUE LOS SERVICIOS ESTÉN LISTOS"

TIMEOUT=300
ELAPSED=0

while [ $ELAPSED -lt $TIMEOUT ]; do
    # Verificar SQL Server
    if docker-compose exec -T sqlserver /opt/mssql-tools18/bin/sqlcmd -S localhost -C -U sa -P "NestleAdmin@2024" -Q "SELECT 1" > /dev/null 2>&1; then
        print_success "SQL Server está listo"
        break
    fi
    
    echo "Esperando SQL Server... ($ELAPSED/$TIMEOUT segundos)"
    sleep 10
    ELAPSED=$((ELAPSED + 10))
done

ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
    # Verificar PostgreSQL
    if docker-compose exec -T postgres pg_isready -U odoo > /dev/null 2>&1; then
        print_success "PostgreSQL está listo"
        break
    fi
    
    echo "Esperando PostgreSQL... ($ELAPSED/$TIMEOUT segundos)"
    sleep 10
    ELAPSED=$((ELAPSED + 10))
done

# Inicializar Odoo si la BD existe pero aún no tiene esquema (primera ejecución)
if ! docker-compose exec -T -e PGPASSWORD=odoo postgres psql -U odoo -d odoo_production -tAc \
    "SELECT 1 FROM information_schema.tables WHERE table_name='ir_module_module' LIMIT 1" 2>/dev/null | grep -q 1; then
    print_info "Instalando módulos base de Odoo (puede tardar varios minutos)..."
    docker-compose stop odoo 2>/dev/null || true
    docker-compose run --rm odoo odoo --config=/etc/odoo/odoo.conf -d odoo_production -i base --stop-after-init --without-demo=all
    docker-compose start odoo
    print_success "Base de datos Odoo inicializada"
fi

ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
    # Verificar Odoo (login responde 200 cuando la BD está lista)
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8069/web/login 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "303" ]; then
        print_success "Odoo está listo"
        break
    fi
    
    echo "Esperando Odoo... ($ELAPSED/$TIMEOUT segundos)"
    sleep 15
    ELAPSED=$((ELAPSED + 15))
done

# ========================================
# INICIALIZAR DATA WAREHOUSE
# ========================================

print_header "INICIALIZANDO DATA WAREHOUSE"

# Crear base de datos
print_info "Creando base de datos nestle_dw..."
docker-compose exec -T sqlserver /opt/mssql-tools18/bin/sqlcmd -S localhost -C -U sa -P "NestleAdmin@2024" -Q "CREATE DATABASE nestle_dw" 2>/dev/null || print_info "Base de datos ya existe"

sleep 5

# Ejecutar scripts
print_info "Ejecutando scripts SQL..."
docker-compose exec -T sqlserver /opt/mssql-tools18/bin/sqlcmd -S localhost -C -U sa -P "NestleAdmin@2024" -i /docker-entrypoint-initdb.d/01_data_warehouse.sql 2>&1 | tail -5

sleep 5

print_info "Insertando datos de ejemplo..."
docker-compose exec -T sqlserver /opt/mssql-tools18/bin/sqlcmd -S localhost -C -U sa -P "NestleAdmin@2024" -i /docker-entrypoint-initdb.d/02_datos_ejemplo.sql 2>&1 | tail -5

print_success "Data Warehouse inicializado"

# ========================================
# PORTAINER - reinicio para evitar timeout de instalación
# ========================================
# Si nadie completa el registro de admin en ~5 min, Portainer se bloquea.
# Reiniciar aquí deja la UI lista cuando el resto del sistema ya está arriba.
print_info "Reiniciando Portainer (listo para registro de administrador)..."
docker-compose restart portainer > /dev/null 2>&1 || true
sleep 5
print_success "Portainer disponible en http://localhost:9000"

# ========================================
# INFORMACIÓN DE ACCESO
# ========================================

print_header "SISTEMA LISTO - INFORMACIÓN DE ACCESO"

echo ""
echo -e "${YELLOW}WEB INTERFACES:${NC}"
echo -e "  Odoo ERP/CRM: ${GREEN}http://localhost:8069${NC}"
echo -e "  PGAdmin: ${GREEN}http://localhost:5050${NC}"
echo -e "  Portainer (Contenedores): ${GREEN}http://localhost:9000${NC}"

echo ""
echo -e "${YELLOW}CREDENCIALES:${NC}"
echo -e "  Odoo:"
echo -e "    Usuario: ${GREEN}admin${NC}"
echo -e "    Contraseña: ${GREEN}admin${NC}"
echo ""
echo -e "  SQL Server:"
echo -e "    Usuario: ${GREEN}sa${NC}"
echo -e "    Contraseña: ${GREEN}NestleAdmin@2024${NC}"
echo -e "    Base de datos: ${GREEN}nestle_dw${NC}"
echo ""
echo -e "  PostgreSQL (Odoo):"
echo -e "    Usuario: ${GREEN}odoo${NC}"
echo -e "    Contraseña: ${GREEN}odoo${NC}"
echo -e "    Base de datos: ${GREEN}odoo_production${NC}"
echo ""
echo -e "  PGAdmin:"
echo -e "    Usuario: ${GREEN}admin@nestle.com${NC}"
echo -e "    Contraseña: ${GREEN}PGAdmin@2024${NC}"
echo ""
echo -e "  Portainer:"
echo -e "    Usuario: ${GREEN}admin${NC}"
echo -e "    Contraseña: ${GREEN}admin12345678${NC}"
echo -e "    (Regístralos en el primer acceso a http://localhost:9000)"
echo -e "    Si ves 'timed out', ejecuta: ${YELLOW}docker compose restart portainer${NC}"

echo ""
echo -e "${YELLOW}CONEXIÓN HERRAMIENTAS:${NC}"
echo -e "  SQL Server Host: ${GREEN}localhost:1433${NC}"
echo -e "  PostgreSQL Host: ${GREEN}localhost:5432${NC}"
echo -e "  Redis Host: ${GREEN}localhost:6379${NC}"

echo ""
echo -e "${YELLOW}SIGUIENTES PASOS:${NC}"
echo -e "  1. Portainer → http://localhost:9000 (registrar admin, ver contenedores)"
echo -e "  2. Odoo → http://localhost:8069 (admin / admin — ERP principal)"
echo -e "  3. PGAdmin → http://localhost:5050 (PostgreSQL de Odoo)"
echo -e "  4. Instalar en Odoo: CRM, Ventas, Inventario"
echo -e "  5. Power BI → SQL Server localhost:1433 (nestle_dw)"

echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${GREEN}SISTEMA LISTO PARA USAR${NC}"
echo -e "${BLUE}=========================================${NC}"

# Ver logs
echo ""
echo "Para ver logs en tiempo real:"
echo -e "  ${YELLOW}docker-compose logs -f odoo${NC}"
echo -e "  ${YELLOW}docker-compose logs -f etl-service${NC}"

exit 0
