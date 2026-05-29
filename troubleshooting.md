# GUÍA RÁPIDA - COMANDOS Y TROUBLESHOOTING

## 🚀 INICIO RÁPIDO

```bash
# Iniciar TODO el sistema
chmod +x start.sh && ./start.sh

# Esperar 3-5 minutos (primer arranque es más lento)
# Acceder a: http://localhost:8069 (admin/admin)
```

---

## 🔧 COMANDOS ESENCIALES

### Ver Estado de Servicios
```bash
# Estado general
docker-compose ps

# Formato detallado
docker-compose ps -a

# Ver IPs de contenedores
docker-compose exec odoo hostname -I
docker-compose exec postgres hostname -I
docker-compose exec sqlserver hostname -I
```

### Ver Logs
```bash
# Logs generales
docker-compose logs

# Logs en tiempo real (Ctrl+C para salir)
docker-compose logs -f

# Logs de servicio específico
docker-compose logs -f odoo
docker-compose logs -f postgres
docker-compose logs -f sqlserver
docker-compose logs -f etl-service
docker-compose logs -f redis

# Últimas 100 líneas
docker-compose logs --tail 100 odoo

# Logs de un período específico
docker-compose logs --since 1h odoo
```

### Reiniciar Servicios
```bash
# Reiniciar uno
docker-compose restart odoo

# Reiniciar todos
docker-compose restart

# Pausar (sin eliminar)
docker-compose stop

# Reanudar
docker-compose start

# Detener y eliminar (mantiene volúmenes)
docker-compose down

# Detener y eliminar TODO incluyendo volúmenes
docker-compose down -v  # ⚠️ BORRA DATOS
```

### Ejecutar Comandos en Contenedores
```bash
# Dentro de Odoo
docker-compose exec odoo /bin/bash

# Dentro de PostgreSQL
docker-compose exec postgres psql -U odoo -d odoo_production

# Dentro de SQL Server
docker-compose exec sqlserver /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P "NestleAdmin@2024"

# Dentro de ETL
docker-compose exec etl-service python etl_nestle.py

# Dentro de Redis
docker-compose exec redis redis-cli
```

---

## 🐛 TROUBLESHOOTING

### 1. Odoo no carga (localhost:8069)

**Síntomas**: Conexión rechazada, timeout, error 502

**Diagnóstico**:
```bash
# Ver si está corriendo
docker-compose ps | grep odoo

# Ver logs
docker-compose logs odoo | tail -50

# Verificar conectividad a PostgreSQL
docker-compose exec odoo curl -v postgres:5432

# Comprobar salud
docker-compose exec odoo curl http://localhost:8069/web/health
```

**Soluciones**:
```bash
# Opción 1: Reiniciar
docker-compose restart odoo
# Esperar 2-3 minutos

# Opción 2: Reconstruir
docker-compose up -d --no-deps --build odoo
# Esperar 5 minutos

# Opción 3: Verificar PostgreSQL está listo
docker-compose exec postgres pg_isready -U odoo
# Debe retornar "accepting connections"

# Opción 4: Limpiar y empezar
docker-compose down -v
docker-compose up -d
# Esperar 10 minutos (primer arranque completo)
```

**Causas comunes**:
- PostgreSQL no está listo → esperar
- Puertos en uso → cambiar en docker-compose.yml
- Insuficiente RAM → aumentar memoria asignada a Docker
- Odoo necesita configuración inicial → acceder a http://localhost:8069/web/setup

---

### 2. PostgreSQL no se conecta

**Síntomas**: Error "connection refused", "role odoo does not exist"

**Diagnóstico**:
```bash
# Ver estado
docker-compose ps | grep postgres

# Ver logs
docker-compose logs postgres | tail -50

# Probar conectividad
docker-compose exec postgres pg_isready -U odoo

# Conectar directamente
docker-compose exec postgres psql -U odoo -d odoo_production
```

**Soluciones**:
```bash
# Opción 1: Reiniciar
docker-compose restart postgres
sleep 30

# Opción 2: Verificar volumen
docker volume ls | grep postgres_data

# Opción 3: Recrear (⚠️ BORRA DATOS)
docker-compose down -v
docker-compose up -d postgres
sleep 60

# Opción 4: Ejecutar inicialización manual
docker-compose exec postgres psql -U postgres -c "CREATE DATABASE odoo_production;"
docker-compose exec postgres psql -U postgres -c "CREATE USER odoo WITH PASSWORD 'odoo';"
docker-compose exec postgres psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE odoo_production TO odoo;"
```

---

### 3. SQL Server no responde

**Síntomas**: Conexión rechazada puerto 1433, error ODBC

**Diagnóstico**:
```bash
# Ver estado
docker-compose ps | grep sqlserver

# Ver logs
docker-compose logs sqlserver | tail -100

# Probar conexión
docker-compose exec sqlserver /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P "NestleAdmin@2024" -Q "SELECT @@version"

# Ver si escucha en puerto
docker-compose exec sqlserver netstat -an | grep 1433
```

**Soluciones**:
```bash
# Opción 1: Reiniciar
docker-compose restart sqlserver
sleep 30

# Opción 2: Ver si es problema de memoria
# SQL Server necesita 2-3 GB mínimo
docker stats sqlserver

# Opción 3: Recrear (⚠️ BORRA DATA WAREHOUSE)
docker-compose down sqlserver
docker volume rm sistema-crm-bi_sqlserver_data  # ⚠️
docker-compose up -d sqlserver
sleep 60

# Opción 4: Recrear base de datos
docker-compose exec sqlserver /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P "NestleAdmin@2024" -Q "CREATE DATABASE nestle_dw;"

# Opción 5: Ejecutar scripts manualmente
docker-compose exec sqlserver /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P "NestleAdmin@2024" -i /docker-entrypoint-initdb.d/01_data_warehouse.sql
docker-compose exec sqlserver /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P "NestleAdmin@2024" -i /docker-entrypoint-initdb.d/02_datos_ejemplo.sql
```

**Nota**: SQL Server 2019 en Linux requiere mínimo 2GB RAM, idealmente 4GB+

---

### 4. ETL no ejecuta

**Síntomas**: Logs vacíos, servicio se reinicia continuamente, sin cambios en DW

**Diagnóstico**:
```bash
# Ver estado del contenedor
docker-compose ps | grep etl

# Ver logs
docker-compose logs etl-service | tail -100

# Ejecutar manualmente
docker-compose exec etl-service python etl_nestle.py

# Verificar archivo de log
docker-compose exec etl-service ls -la logs/

# Ver contenido del log
docker-compose exec etl-service tail -50 logs/etl.log
```

**Soluciones**:
```bash
# Opción 1: Verificar conectividad a Odoo
docker-compose exec etl-service curl http://odoo:8069/web/health

# Opción 2: Verificar conectividad a SQL Server
docker-compose exec etl-service /opt/mssql-tools/bin/sqlcmd -S sqlserver:1433 -U sa -P "NestleAdmin@2024" -Q "SELECT 1"

# Opción 3: Reinstalar dependencias
docker-compose exec etl-service pip install -r requirements.txt

# Opción 4: Reconstruir contenedor
docker-compose up -d --no-deps --build etl-service

# Opción 5: Ejecutar con debug
docker-compose exec etl-service python -u etl_nestle.py
```

**Causas comunes**:
- Odoo no está ready → esperar a que Odoo esté listo
- SQL Server no accessible → verificar conectividad
- Variables de entorno no definidas → revisar .env
- Módulos Python no instalados → reinstalar requirements.txt

---

### 5. Base de datos llena / Sin espacio

**Síntomas**: Error "No space left on device", contenedores se paran

**Diagnóstico**:
```bash
# Ver uso de disco Docker
docker system df

# Ver uso de volúmenes
docker volume ls -q | xargs -I {} sh -c 'echo {} && docker inspect {} | grep -A 5 Mountpoint'

# Ver tamaño de base de datos PostgreSQL
docker-compose exec postgres du -sh /var/lib/postgresql/data

# Ver tamaño de base de datos SQL Server
docker-compose exec sqlserver du -sh /var/opt/mssql/data
```

**Soluciones**:
```bash
# Opción 1: Limpiar datos obsoletos
docker system prune -a --volumes  # ⚠️ BORRA TODO

# Opción 2: Aumentar espacio del disco (VM)
# Si es una VM, aumentar tamaño de disco

# Opción 3: Limpiar logs viejos
docker-compose exec etl-service find logs -name "*.log" -mtime +30 -delete

# Opción 4: Optimizar PostgreSQL
docker-compose exec postgres vacuumdb -U odoo -d odoo_production -a -z

# Opción 5: Optimizar SQL Server
docker-compose exec sqlserver /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P "NestleAdmin@2024" -Q "DBCC SHRINKDATABASE (nestle_dw)"

# Ver espacio libre actual
df -h
```

---

### 6. Puertos ya en uso

**Síntomas**: Error "Address already in use", puerto 8069, 5432, 1433, etc.

**Diagnóstico**:
```bash
# Ver qué usa el puerto 8069
lsof -i :8069
# o
netstat -tlnp | grep 8069

# Ver todos los puertos Docker
docker-compose ps
```

**Soluciones**:
```bash
# Opción 1: Cambiar puerto en docker-compose.yml
# Cambiar: "8069:8069" → "8070:8069"
sed -i 's/"8069:8069"/"8070:8069"/' docker-compose.yml

# Opción 2: Matar proceso que usa el puerto
# Encontrar PID y matar
kill -9 <PID>

# Opción 3: Usar contenedor en puerto diferente
docker-compose down
# Editar docker-compose.yml con puertos nuevos
docker-compose up -d

# Opción 4: Usar puerto no estándar para todo
# Crear archivo docker-compose.override.yml
cat > docker-compose.override.yml << EOF
version: '3.9'
services:
  odoo:
    ports:
      - "8070:8069"
  postgres:
    ports:
      - "5433:5432"
  sqlserver:
    ports:
      - "1434:1433"
  pgadmin:
    ports:
      - "5051:80"
  portainer:
    ports:
      - "9001:9000"
EOF

docker-compose up -d
```

---

### 7. Memoria insuficiente

**Síntomas**: Contenedores mueren, "OOMKilled", sistema lento

**Diagnóstico**:
```bash
# Ver uso de memoria
docker stats

# Ver límites asignados
docker inspect crm-odoo | grep -A 5 Memory

# Ver memoria física disponible
free -h

# Ver si hay swap
swapon -s
```

**Soluciones**:
```bash
# Opción 1: Aumentar límites en docker-compose.yml
services:
  odoo:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G

# Opción 2: Reducir workers en Odoo
# En odoo/config/odoo.conf:
workers = 2  # Reducir de 4 a 2

# Opción 3: Eliminar servicios no necesarios
# Comentar en docker-compose.yml los que no uses

# Opción 4: Aumentar RAM de la máquina/VM
# Si es VM, aumentar memoria asignada

# Opción 5: Habilitar swap en Linux
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## 📊 CONSULTAS ÚTILES SQL

### SQL Server (nestle_dw)

```sql
-- Conectar
sqlcmd -S localhost -U sa -P "NestleAdmin@2024"

-- Ver tablas creadas
USE nestle_dw;
GO
SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES ORDER BY TABLE_NAME;
GO

-- Contar registros
SELECT 'dim_cliente' AS tabla, COUNT(*) AS registros FROM dim_cliente
UNION ALL
SELECT 'dim_producto', COUNT(*) FROM dim_producto
UNION ALL
SELECT 'dim_vendedor', COUNT(*) FROM dim_vendedor
UNION ALL
SELECT 'dim_tiempo', COUNT(*) FROM dim_tiempo
UNION ALL
SELECT 'fact_ventas', COUNT(*) FROM fact_ventas
UNION ALL
SELECT 'fact_inventario', COUNT(*) FROM fact_inventario;
GO

-- Ventas totales
SELECT SUM(monto_neto) AS ingresos_total FROM fact_ventas;
GO

-- Top 5 clientes por volumen
SELECT TOP 5 dc.nombre_cliente, SUM(fv.monto_neto) AS total
FROM fact_ventas fv
JOIN dim_cliente dc ON fv.cliente_id = dc.cliente_id
GROUP BY dc.nombre_cliente
ORDER BY total DESC;
GO

-- Productos más vendidos
SELECT TOP 10 dp.nombre_producto, SUM(fv.cantidad_unidades) AS unidades
FROM fact_ventas fv
JOIN dim_producto dp ON fv.producto_id = dp.producto_id
GROUP BY dp.nombre_producto
ORDER BY unidades DESC;
GO

-- Desempeño de vendedores
SELECT dv.nombre_vendedor, COUNT(fv.venta_id) AS pedidos,
       SUM(fv.monto_neto) AS ingresos,
       SUM(fv.ganancia_bruta) AS ganancia
FROM fact_ventas fv
JOIN dim_vendedor dv ON fv.vendedor_id = dv.vendedor_id
GROUP BY dv.nombre_vendedor
ORDER BY ingresos DESC;
GO
```

### PostgreSQL (odoo_production)

```bash
# Conectar
docker-compose exec postgres psql -U odoo -d odoo_production

# Ver tablas principales
\dt res.*
\dt sale.*
\dt product.*

# Contar partners (clientes)
SELECT COUNT(*) FROM res_partner WHERE is_company = true;

-- Contar productos
SELECT COUNT(*) FROM product_product WHERE active = true;

-- Órdenes de venta
SELECT COUNT(*) FROM sale_order;

-- Líneas de venta
SELECT COUNT(*) FROM sale_order_line;

-- Salir
\q
```

---

## 📈 MONITOREO EN TIEMPO REAL

```bash
# Terminal 1: Monitorear recursos
watch -n 1 'docker stats --no-stream'

# Terminal 2: Logs Odoo
docker-compose logs -f odoo

# Terminal 3: Logs ETL
docker-compose logs -f etl-service

# Terminal 4: Logs SQL Server
docker-compose logs -f sqlserver

# Terminal 5: Ver procesos
docker-compose ps -a
```

---

## 🔄 BACKUP Y RESTORE

### PostgreSQL

```bash
# Backup
docker-compose exec postgres pg_dump -U odoo odoo_production > backup_odoo.sql

# Backup comprimido
docker-compose exec postgres pg_dump -U odoo odoo_production | gzip > backup_odoo.sql.gz

# Restore
docker-compose exec -T postgres psql -U odoo odoo_production < backup_odoo.sql

# Restore comprimido
gunzip < backup_odoo.sql.gz | docker-compose exec -T postgres psql -U odoo odoo_production
```

### SQL Server

```bash
# Backup
docker-compose exec sqlserver /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P "NestleAdmin@2024" \
  -Q "BACKUP DATABASE [nestle_dw] TO DISK = '/var/opt/mssql/backup/nestle_dw.bak'"

# Restore
docker-compose exec sqlserver /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P "NestleAdmin@2024" \
  -Q "RESTORE DATABASE [nestle_dw] FROM DISK = '/var/opt/mssql/backup/nestle_dw.bak'"
```

---

## 🔐 CAMBIAR CONTRASEÑAS

```bash
# SQL Server SA
docker-compose exec sqlserver /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P "NestleAdmin@2024" \
  -Q "ALTER LOGIN sa WITH PASSWORD='NuevaContraseña123!'"

# PostgreSQL
docker-compose exec postgres psql -U postgres -c "ALTER USER odoo WITH PASSWORD 'nueva_contraseña';"

# Odoo (vía interfaz web)
# Ir a http://localhost:8069 → Settings → Users → Administrator

# PGAdmin (en docker-compose.yml)
# Cambiar PGADMIN_DEFAULT_PASSWORD y reiniciar
```

---

## 📞 CONTACTO SOPORTE

Si los problemas persisten:
1. Revisar logs completos: `docker-compose logs > sistema_completo.log`
2. Ejecutar: `docker-compose ps -a` y guardar salida
3. Ejecutar: `docker system df` y guardar salida
4. Crear archivo SOPORTE.txt con toda la información

---

**¡Última actualización**: 2024  
**Versión**: 1.0