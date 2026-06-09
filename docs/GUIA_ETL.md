# Guía ETL — Sincronización Odoo → SQL Server

El servicio **ETL** (`crm-etl`) extrae datos operativos de **Odoo** y los carga en el **Data Warehouse** `nestle_dw` en SQL Server, para consumo en **Power BI** y **SSMS**.

---

## Resumen

| Aspecto | Detalle |
|---------|---------|
| Contenedor | `crm-etl` |
| Script | `etl/etl_nestle.py` |
| Frecuencia | Cada **1 hora** (automático) + al arrancar el contenedor |
| Origen | Odoo (XML-RPC) — http://odoo:8069 |
| Destino | SQL Server — `sqlserver,1433` / BD `nestle_dw` |
| Logs | `etl/logs/etl.log` |

---

## Configuración (variables de entorno)

Definidas en `docker-compose.yml` para el servicio `etl-service`:

| Variable | Valor por defecto |
|----------|-------------------|
| `ODOO_URL` | `http://odoo:8069` |
| `ODOO_DB` | `odoo_production` |
| `ODOO_USER` | `admin` |
| `ODOO_PASSWORD` | `admin` |
| `SQL_SERVER` | `sqlserver,1433` |
| `SQL_USER` | `sa` |
| `SQL_PASSWORD` | `NestleAdmin@2024` |
| `SQL_DB` | `nestle_dw` |

---

## Mapeo de datos

| Proceso ETL | Modelo Odoo | Tabla SQL Server |
|-------------|-------------|------------------|
| Clientes | `res.partner` (empresas) | `dim_cliente` |
| Productos | `product.product` | `dim_producto` |
| Vendedores | `res.users` | `dim_vendedor` |
| Ventas | `sale.order` | `fact_ventas` |
| Inventario | (stock) | `fact_inventario` |

---

## Ejecución manual

Desde la carpeta del proyecto:

```powershell
docker compose exec etl-service python etl_nestle.py
```

Modo scheduler (ya activo en el contenedor):

```powershell
docker compose exec etl-service python etl_nestle.py --scheduler
```

---

## Verificar resultados

### Logs

```powershell
docker compose logs etl-service --tail 50
Get-Content etl\logs\etl.log -Tail 30
```

### SQL Server (SSMS)

```sql
USE nestle_dw;

SELECT COUNT(*) AS clientes FROM dim_cliente;
SELECT COUNT(*) AS productos FROM dim_producto;
SELECT COUNT(*) AS ventas FROM fact_ventas;

SELECT TOP 10 *
FROM fact_ventas
ORDER BY fecha_pedido DESC;
```

---

## Requisitos para que el ETL traiga datos de Odoo

1. **Odoo** accesible y con módulo **Ventas** instalado.
2. **Clientes** creados como empresa (`is_company = true` en Odoo).
3. **Productos** con precios definidos.
4. **Pedidos de venta confirmados** (no solo borradores).
5. Contenedores `crm-odoo`, `crm-sqlserver` y `crm-etl` en ejecución.

---

## Flujo recomendado de prueba

1. Crear en Odoo: 1 cliente empresa, 1 producto, 1 cotización → **Confirmar**.
2. Ejecutar ETL manual (comando arriba).
3. Consultar `fact_ventas` en SSMS.
4. **Actualizar** el informe en Power BI.

---

## Errores frecuentes

| Error | Solución |
|-------|----------|
| No se pudo conectar a Odoo | Verificar `http://localhost:8069` y credenciales admin/admin |
| Error ODBC SQL Server | Verificar `crm-sqlserver` healthy |
| 0 registros leídos | No hay datos que cumplan filtros en Odoo; confirmar pedidos |
| Duplicados | Normal en re-ejecuciones; el script usa `IF NOT EXISTS` en dimensiones |

---

Ver también: [README.md](../README.md) — guía completa del sistema.
