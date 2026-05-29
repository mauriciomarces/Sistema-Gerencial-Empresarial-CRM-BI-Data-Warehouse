# Sistema Gerencial Nestlé — CRM, Data Warehouse y Business Intelligence

Solución empresarial completa con **Odoo (ERP/CRM)**, **SQL Server (Data Warehouse)**, **ETL automatizado** y **Power BI**, desplegada en **Docker** con un solo comando.

---

## Tabla de contenidos

1. [Inicio rápido (un comando)](#1-inicio-rápido-un-comando)
2. [Requisitos del equipo](#2-requisitos-del-equipo)
3. [Recibir el proyecto en RAR e instalar](#3-recibir-el-proyecto-en-rar-e-instalar)
4. [Arquitectura: para qué sirve cada pieza](#4-arquitectura-para-qué-sirve-cada-pieza)
5. [Flujo de datos (Odoo → ETL → SQL → Power BI)](#5-flujo-de-datos-odoo--etl--sql--power-bi)
6. [Servicios, puertos y URLs](#6-servicios-puertos-y-urls)
7. [Credenciales (referencia rápida)](#7-credenciales-referencia-rápida)
8. [Guía por componente](#8-guía-por-componente)
9. [SSMS — conectar a SQL Server](#9-ssms--conectar-a-sql-server)
10. [Power BI — conectar sin errores](#10-power-bi--conectar-sin-errores)
11. [Odoo — uso y automatización](#11-odoo--uso-y-automatización)
12. [ETL — sincronización Odoo → SQL Server](#12-etl--sincronización-odoo--sql-server)
13. [Prueba de punta a punta](#13-prueba-de-punta-a-punta)
14. [Comandos útiles](#14-comandos-útiles)
15. [Problemas frecuentes y soluciones](#15-problemas-frecuentes-y-soluciones)
16. [Empaquetar y distribuir en RAR](#16-empaquetar-y-distribuir-en-rar)

---

## 1. Inicio rápido (un comando)

### ¿Dónde ejecutar el comando?

1. **Descomprime** el archivo `.rar` en una carpeta simple, por ejemplo:
   ```
   C:\sistemas-empresariales
   ```
   Evita rutas con espacios o caracteres rar si puedes.

2. **Abre Docker Desktop** y espera a que diga *Engine running* (motor en ejecución).

3. **Abre una terminal EN ESA CARPETA** (importante):

   | Sistema | Cómo abrir | Comando |
   |---------|------------|---------|
   | **Windows (recomendado)** | Clic derecho en la carpeta → *Abrir en Terminal* o PowerShell | `.\start.ps1` |
   | **Windows (Git Bash)** | Git Bash en la carpeta del proyecto | `./start.sh` |
   | **Linux / macOS** | Terminal en la carpeta del proyecto | `chmod +x start.sh && ./start.sh` |

4. **Espera 10–20 minutos** la primera vez (descarga imágenes Docker, instala Odoo, crea el data warehouse).

5. Cuando termine, abre en el navegador:
   - **Odoo (principal):** http://localhost:8069
   - **Portainer:** http://localhost:9000

> **Nota:** `start.sh` y `start.ps1` hacen lo mismo. En Windows usa **`start.ps1`** si no tienes Git Bash.

---

## 2. Requisitos del equipo

| Requisito | Mínimo | Recomendado |
|-----------|--------|-------------|
| SO | Windows 10/11 64 bits | Windows 11 |
| RAM | 8 GB | 16 GB |
| Disco libre | 15 GB | 25 GB |
| Docker | Docker Desktop 4.x+ | Última versión |
| Virtualización | Habilitada en BIOS | — |
| Internet | Primera ejecución (descarga imágenes) | — |

### Software opcional (no incluido en Docker)

| Herramienta | Para qué |
|-------------|----------|
| **SSMS** (SQL Server Management Studio) | Ver y consultar `nestle_dw` |
| **Power BI Desktop** | Dashboards sobre el data warehouse |
| **Navegador** (Chrome/Edge) | Odoo, Portainer, pgAdmin |

---

## 3. Recibir el proyecto en RAR e instalar

### Paso a paso para quien recibe el RAR

1. Instalar **Docker Desktop**: https://www.docker.com/products/docker-desktop/
2. Reiniciar el PC si Docker lo pide.
3. Descomprimir el `.rar` con WinRAR o 7-Zip.
4. Entrar a la carpeta descomprimida (debe contener `docker-compose.yml`, `start.ps1`, `README.md`).
5. Abrir **Docker Desktop** → esperar *Engine running*.
6. En PowerShell, dentro de la carpeta:
   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\start.ps1
   ```
   Si PowerShell bloquea scripts, el comando anterior solo aplica a esa ventana.
7. Al finalizar, seguir la sección [Guía por componente](#8-guía-por-componente).

### Si ya ejecutaste el sistema antes

Para un arranque limpio (borra bases de datos anteriores):

```powershell
docker compose down --volumes
.\start.ps1
```

---

## 4. Arquitectura: para qué sirve cada pieza

```
┌─────────────────────────────────────────────────────────────┐
│  USUARIOS DE NEGOCIO          ANALISTAS / DIRECCIÓN          │
│       │                              │                      │
│       ▼                              ▼                      │
│   Odoo (8069)                   Power BI Desktop            │
│   ERP / CRM                     Dashboards / KPIs           │
└───────┬──────────────────────────────┬──────────────────────┘
        │                              │
        ▼                              ▼
   PostgreSQL                    SQL Server (1433)
   (operacional)                 nestle_dw (analítico)
        ▲                              ▲
        │         ETL (crm-etl)        │
        └──────── sincroniza ──────────┘
```

| Componente | Rol | ¿Quién lo usa? |
|------------|-----|----------------|
| **Odoo** | Ventas, clientes, productos, pedidos | Usuario de negocio (día a día) |
| **PostgreSQL** | Base de datos interna de Odoo | Automático (no se toca normalmente) |
| **SQL Server** | Data warehouse (`nestle_dw`) para reportes | Analistas, Power BI, SSMS |
| **ETL** | Copia y transforma datos Odoo → SQL Server | Automático (cada hora) o manual |
| **Power BI** | Gráficos sobre `nestle_dw` | Dirección / analistas |
| **Portainer** | Ver estado de contenedores Docker | Soporte técnico |
| **pgAdmin** | Explorar PostgreSQL de Odoo | Soporte técnico |
| **Redis** | Caché y sesiones de Odoo | Automático |

**Regla de oro:** operas en **Odoo**; analizas en **Power BI**. El puente es el **ETL**.

---

## 5. Flujo de datos (Odoo → ETL → SQL → Power BI)

### Paso 1 — Operación (Odoo)
- Creas clientes, productos y **confirmas pedidos de venta**.
- Todo se guarda en **PostgreSQL** (`odoo_production`).

### Paso 2 — Sincronización (ETL)
- El contenedor `crm-etl` se ejecuta **cada hora** (o manualmente).
- Lee Odoo vía API (XML-RPC): clientes, productos, vendedores, ventas.
- Inserta/actualiza tablas en **SQL Server** (`nestle_dw`):
  - Dimensiones: `dim_cliente`, `dim_producto`, `dim_vendedor`, `dim_tiempo`
  - Hechos: `fact_ventas`, `fact_inventario`

### Paso 3 — Análisis (SQL Server + Power BI)
- **SSMS** o **Power BI** consultan `nestle_dw`.
- Los datos de ejemplo (`02_datos_ejemplo.sql`) ya vienen cargados tras `start.ps1`.
- Los datos **nuevos de Odoo** aparecen después de ejecutar el ETL.

### Paso 4 — Actualizar reportes
- En Power BI: **Inicio → Actualizar**.
- Los gráficos reflejan la última sincronización ETL.

---

## 6. Servicios, puertos y URLs

| Servicio | Contenedor | Puerto | URL / Conexión |
|----------|------------|--------|----------------|
| Odoo ERP/CRM | `crm-odoo` | **8069** | http://localhost:8069 |
| Odoo longpolling | `crm-odoo` | 8072 | (interno) |
| PostgreSQL | `crm-postgres` | **5432** | `localhost:5432` |
| SQL Server | `crm-sqlserver` | **1433** | `127.0.0.1,1433` |
| Redis | `crm-redis` | 6379 | `localhost:6379` |
| pgAdmin | `crm-pgadmin` | **5050** | http://localhost:5050 |
| Portainer | `crm-portainer` | **9000** | http://localhost:9000 |
| Portainer tunnel | `crm-portainer` | 8000 | (agentes remotos) |
| ETL | `crm-etl` | — | Sin puerto web (logs en `etl/logs/`) |

### Verificar que todo está arriba

```powershell
docker compose ps
```

Todos deben estar **Up**; SQL Server, Postgres, Redis y Odoo idealmente **healthy**.

---

## 7. Credenciales (referencia rápida)

> ⚠️ Credenciales de **desarrollo/demo**. Cambiar en producción.

| Sistema | Usuario | Contraseña | Base / Notas |
|---------|---------|------------|--------------|
| **Odoo** | `admin` | `admin` | BD: `odoo_production` |
| **SQL Server** | `sa` | `NestleAdmin@2024` | BD: `nestle_dw` |
| **PostgreSQL** | `odoo` | `odoo` | BD: `odoo_production` |
| **pgAdmin** | `admin@nestle.com` | `PGAdmin@2024` | — |
| **Portainer** | `admin` | `admin12345678` | Crear en **primer acceso** a http://localhost:9000 |
| **ETL → Odoo** | `admin` | `admin` | Configurado en `docker-compose.yml` |

---

## 8. Guía por componente

### 8.1 Odoo — http://localhost:8069

**Qué verás:** pantalla de login.

**Qué hacer la primera vez:**
1. Entrar con `admin` / `admin`.
2. Completar asistente (idioma, país, empresa) si aparece.
3. Ir a **Aplicaciones** e instalar:
   - **Ventas**
   - **CRM** (opcional)
   - **Inventario** (opcional)
4. Menú **Ventas → Cotizaciones** para crear y **Confirmar** pedidos.

**Para qué sirve:** gestión operativa (clientes, productos, ventas). Es la aplicación principal del proyecto.

---

### 8.2 Portainer — http://localhost:9000

**Qué verás:** asistente *New Portainer installation* (si es la primera vez).

**Qué hacer:**
1. Abrir **inmediatamente** tras `start.ps1` (el script reinicia Portainer al final).
2. Crear administrador:
   - Usuario: **`admin`**
   - Contraseña: **`admin12345678`**
3. Elegir **Get Started** → entorno **Docker** → **Connect**.
4. Menú **Containers**: deben aparecer 7 contenedores `crm-*` en verde.

**Si aparece "timed out for security purposes":**
```powershell
docker compose restart portainer
```
Espera 10 segundos y recarga http://localhost:9000.

**Para qué sirve:** reiniciar contenedores, ver logs, comprobar que Docker está bien. No es donde se vende ni se factura.

---

### 8.3 pgAdmin — http://localhost:5050

**Login:** `admin@nestle.com` / `PGAdmin@2024`

**Registrar servidor PostgreSQL:**
| Campo | Valor |
|-------|-------|
| Host | `postgres` (desde pgAdmin en Docker) o `host.docker.internal` |
| Puerto | `5432` |
| Usuario | `odoo` |
| Contraseña | `odoo` |
| Base de datos | `odoo_production` |

**Para qué sirve:** inspección técnica de la BD de Odoo. Uso opcional.

---

### 8.4 SSMS — SQL Server

Ver sección [9. SSMS](#9-ssms--conectar-a-sql-server).

---

### 8.5 Power BI

Ver sección [10. Power BI](#10-power-bi--conectar-sin-errores).

---

## 9. SSMS — conectar a SQL Server

1. Abrir **SQL Server Management Studio**.
2. **Conectar** → pestaña *Propiedades de conexión* o diálogo clásico:

| Campo | Valor |
|-------|-------|
| Tipo de servidor | Motor de base de datos |
| Servidor | `127.0.0.1,1433` |
| Autenticación | **Autenticación de SQL Server** |
| Inicio de sesión | `sa` |
| Contraseña | `NestleAdmin@2024` |

3. Opciones → **Confiar en el certificado del servidor** (si aparece).
4. Conectar → expandir **Bases de datos** → **`nestle_dw`**.

**Tablas principales:**
- `dim_cliente`, `dim_producto`, `dim_vendedor`, `dim_tiempo`
- `fact_ventas`, `fact_inventario`

**Consulta de prueba:**
```sql
USE nestle_dw;
SELECT COUNT(*) AS total_ventas FROM fact_ventas;
SELECT TOP 5 * FROM dim_cliente;
```

---

## 10. Power BI — conectar sin errores

### Requisitos
- **Power BI Desktop** instalado.
- Docker con `crm-sqlserver` **Up (healthy)**.
- Base `nestle_dw` creada (lo hace `start.ps1`).

### Conexión correcta (evita error SSPI)

El error *"The target principal name is incorrect. Cannot generate SSPI context"* ocurre cuando Power BI intenta **autenticación Windows**. SQL Server en Docker solo acepta **autenticación SQL**.

**Pasos:**

1. Power BI Desktop → **Obtener datos** → **SQL Server** → **Conectar**.
2. Configuración:

| Campo | Valor |
|-------|-------|
| Servidor | **`127.0.0.1,1433`** (usar IP, no `localhost`) |
| Base de datos | `nestle_dw` |
| Modo | **Importar** (recomendado al empezar) |

3. Credenciales → **Base de datos** (no Windows):
   - Usuario: `sa`
   - Contraseña: `NestleAdmin@2024`

4. **Opciones avanzadas** → cadena adicional:
   ```
   Encrypt=True;TrustServerCertificate=True;Authentication=SqlPassword;
   ```

5. Seleccionar tablas `dim_*` y `fact_*` → **Cargar**.

6. En **Vista de modelo**, crear relaciones entre hechos y dimensiones (por `cliente_id`, `producto_id`, etc.).

### Si guardaste credenciales incorrectas
**Archivo** → **Opciones y configuración** → **Configuración de origen de datos** → eliminar entradas de `localhost` / `127.0.0.1` y reconectar.

### Actualizar datos después del ETL
**Inicio** → **Actualizar** (o programar actualización en producción).

---

## 11. Odoo — uso y automatización

### Evitar crear todo uno por uno

| Método | Cómo |
|--------|------|
| **Importar CSV** | Contactos / Productos → menú ⋮ → **Importar registros** |
| **Duplicar** | Abrir un registro → **Acción** → **Duplicar** |
| **Acciones automatizadas** | Ajustes → Técnico → Automatización → Acciones automatizadas |
| **Acciones planificadas** | Ajustes → Técnico → Automatización → Acciones planificadas (cron) |
| **Plantillas de cotización** | Ventas → Configuración → Plantillas |

### Datos en SQL Server vs Odoo

- Tras `start.ps1`, Power BI/SSMS muestran **datos de ejemplo** (`02_datos_ejemplo.sql`).
- Para ver **tus ventas de Odoo** en SQL/Power BI: crea pedidos en Odoo → ejecuta ETL → actualiza Power BI.

---

## 12. ETL — sincronización Odoo → SQL Server

Documentación ampliada: [docs/GUIA_ETL.md](docs/GUIA_ETL.md)

### Automático
El contenedor `crm-etl` ejecuta el ETL **cada hora** y al iniciar.

### Manual (recomendado para pruebas)

```powershell
docker compose exec etl-service python etl_nestle.py
```

### Ver logs

```powershell
docker compose logs etl-service --tail 50
type etl\logs\etl.log
```

### Qué sincroniza

| Origen (Odoo) | Destino (SQL Server) |
|---------------|----------------------|
| `res.partner` (empresas) | `dim_cliente` |
| `product.product` | `dim_producto` |
| Usuarios / vendedores | `dim_vendedor` |
| Pedidos de venta | `fact_ventas` |

---

## 13. Prueba de punta a punta

Sigue esta checklist para validar todo el sistema:

- [ ] `docker compose ps` — 7 contenedores Up
- [ ] http://localhost:8069 — login Odoo `admin` / `admin`
- [ ] Odoo: instalar **Ventas**, crear 1 cliente, 1 producto, 1 cotización **confirmada**
- [ ] `docker compose exec etl-service python etl_nestle.py` — sin errores en log
- [ ] SSMS: `SELECT TOP 5 * FROM fact_ventas ORDER BY fecha_pedido DESC`
- [ ] Power BI: **Actualizar** y ver cambios (puede haber retraso si el ETL no encontró ventas confirmadas aún)
- [ ] http://localhost:9000 — Portainer con contenedores en verde

---

## 14. Comandos útiles

```powershell
# Ir siempre a la carpeta del proyecto
Set-Location C:\sistemas-empresariales

# Levantar todo (si ya está configurado)
docker compose up -d

# Parar todo
docker compose down

# Parar y borrar volúmenes (instalación limpia)
docker compose down --volumes

# Logs de un servicio
docker compose logs -f odoo
docker compose logs -f sqlserver
docker compose logs -f etl-service

# Reiniciar un servicio
docker compose restart odoo
docker compose restart portainer

# ETL manual
docker compose exec etl-service python etl_nestle.py
```

---

## 15. Problemas frecuentes y soluciones

### Docker / arranque

| Problema | Causa | Solución |
|----------|-------|----------|
| `docker: command not found` | Docker no instalado o no en PATH | Instalar Docker Desktop y reiniciar |
| Build ETL falla `apt-key: not found` | Dockerfile antiguo | Usar la versión actual del repo (ya corregido) |
| `crm-sqlserver` unhealthy, Access denied | Volumen SQL con permisos incorrectos | `docker compose down --volumes` y `.\start.ps1` |
| `df: /home: No such file or directory` | Script en Windows | Usar `start.ps1` o `start.sh` actualizado |

### Odoo

| Problema | Causa | Solución |
|----------|-------|----------|
| `no such option: --db_name` | Opción CLI inválida en Odoo 17 | Usar `docker-compose.yml` actual (config en `odoo.conf`) |
| http://localhost:8069 rechaza conexión | Contenedor reiniciando | `docker compose logs odoo`; esperar init o `docker compose restart odoo` |
| Error 500 en login | BD sin tablas Odoo | `start.ps1` reinstala `base`; o ejecutar init manual del script |

### Portainer

| Problema | Causa | Solución |
|----------|-------|----------|
| "timed out for security purposes" | No se completó registro admin en ~5 min | `docker compose restart portainer` y registrar **admin** / **admin12345678** de inmediato |

### Power BI / SSMS

| Problema | Causa | Solución |
|----------|-------|----------|
| SSPI / target principal name incorrect | Autenticación Windows | Usar **`127.0.0.1,1433`**, auth **SQL**, `TrustServerCertificate=True` |
| Login failed for user 'sa' | Contraseña incorrecta | `NestleAdmin@2024` exacta |
| No hay tablas | BD no inicializada | Ejecutar `.\start.ps1` o scripts en `sql/init/` |

### ETL

| Problema | Causa | Solución |
|----------|-------|----------|
| No aparecen ventas nuevas en SQL | ETL no ejecutado o sin pedidos confirmados en Odoo | Confirmar pedidos en Odoo + ETL manual |
| Error conexión Odoo | Odoo caído o credenciales | Verificar http://localhost:8069 y vars en `docker-compose.yml` |

---

## 16. Empaquetar y distribuir en RAR

### Para quien prepara el paquete

1. **Incluir** en el RAR:
   - Toda la carpeta del proyecto **excepto** lo listado abajo
   - `README.md`, `start.ps1`, `start.sh`, `docker-compose.yml`
   - Carpetas: `odoo/`, `etl/`, `sql/`, `scripts/`

2. **NO incluir** (se regeneran solos):
   - `.git/` (si existe)
   - `etl/logs/*.log`
   - Volúmenes Docker (no están en la carpeta)
   - Archivos temporales de IDE

3. **Comprimir:**
   - Clic derecho en la carpeta `sistemas-empresariales` → WinRAR → *Añadir al archivo...*
   - Nombre sugerido: `sistemas-empresariales-v1.rar`

4. **Instrucciones para el receptor** (incluir en el email o README):
   ```
   1. Instalar Docker Desktop
   2. Descomprimir el RAR en C:\sistemas-empresariales
   3. Abrir Docker Desktop (Engine running)
   4. PowerShell en esa carpeta:
      Set-ExecutionPolicy -Scope Process Bypass
      .\start.ps1
   5. Leer README.md sección "Inicio rápido"
   ```

### Tamaño aproximado del RAR
~2–5 MB (sin imágenes Docker). Las imágenes se descargan en la primera ejecución (~5–8 GB).

---

## Estructura del proyecto

```
sistemas-empresariales/
├── README.md                 ← Esta guía
├── start.ps1                 ← Arranque Windows (recomendado)
├── start.sh                  ← Arranque Linux / Git Bash
├── docker-compose.yml        ← Definición de los 7 servicios
├── odoo/
│   ├── config/odoo.conf      ← Configuración Odoo
│   └── addons/               ← Módulos personalizados (vacío al inicio)
├── etl/
│   ├── etl_nestle.py         ← Script ETL
│   ├── Dockerfile
│   └── logs/                 ← Logs del ETL
├── sql/
│   ├── 01_data_warehouse.sql
│   ├── 02_datos_ejemplo.sql
│   └── init/                 ← Scripts montados en SQL Server
├── scripts/                  ← Scripts auxiliares
└── docs/
    └── GUIA_ETL.md           ← Detalle del ETL
```

---

## Soporte y documentación adicional

| Archivo | Contenido |
|---------|-----------|
| `LIENZO.md` | Visión ejecutiva del proyecto |
| `RESUMEN.txt` | Resumen técnico extendido |
| `troubleshooting.md` | Solución de problemas detallada |
| `docs/GUIA_ETL.md` | ETL paso a paso |

---

**Sistema Gerencial Nestlé — CRM + BI + Data Warehouse**  
Versión documentada: 2026 — Docker Compose, Odoo 17, SQL Server 2019, Power BI Desktop.
