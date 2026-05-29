#!/bin/bash
# ========================================
# SCRIPT DE INICIALIZACIÓN SQL SERVER
# Crea el Data Warehouse y tablas
# ========================================

SQL_SERVER=${SQL_SERVER:-sqlserver}
SQL_PORT=${SQL_PORT:-1433}
SQL_USER=${SQL_USER:-sa}
SQL_PASSWORD=${SQL_PASSWORD:-NestleAdmin@2024}

echo "========================================="
echo "Inicializando SQL Server Data Warehouse"
echo "========================================="

# Esperar a que SQL Server esté listo
echo "Esperando a que SQL Server esté disponible..."
for i in {1..30}; do
    if /opt/mssql-tools18/bin/sqlcmd -S ${SQL_SERVER},${SQL_PORT} -C -U ${SQL_USER} -P "${SQL_PASSWORD}" -Q "SELECT 1" > /dev/null 2>&1; then
        echo "✓ SQL Server está disponible"
        break
    fi
    echo "Intento $i/30..."
    sleep 5
done

# Ejecutar scripts de creación
echo ""
echo "Creando Data Warehouse..."

/opt/mssql-tools18/bin/sqlcmd -S ${SQL_SERVER},${SQL_PORT} -C -U ${SQL_USER} -P "${SQL_PASSWORD}" -i /docker-entrypoint-initdb.d/01_data_warehouse.sql

echo ""
echo "Insertando datos de ejemplo..."

/opt/mssql-tools18/bin/sqlcmd -S ${SQL_SERVER},${SQL_PORT} -C -U ${SQL_USER} -P "${SQL_PASSWORD}" -i /docker-entrypoint-initdb.d/02_datos_ejemplo.sql

echo ""
echo "✓ Inicialización completada"

exit 0