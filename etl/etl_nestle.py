#!/usr/bin/env python3
"""
ETL NESTLE v2.0 - Extrae datos de Odoo e inserta en SQL Server Data Warehouse
Modelo: Estrella mejorado (5 dimensiones + 1 hecho)
Autor: Sistema CRM BI
Version: 2.0
"""

import os
import sys
import logging
import traceback
from datetime import datetime, timedelta
import time
from dotenv import load_dotenv
import schedule

# Importaciones SQL
try:
    import pyodbc
except ImportError:
    pyodbc = None
    logging.warning("pyodbc no instalado")

# Importaciones XML-RPC Odoo
try:
    import xmlrpc.client
except ImportError:
    xmlrpc = None
    logging.warning("xmlrpc no disponible")

# ========================================
# CONFIGURACIÓN
# ========================================

load_dotenv()

# Configuración Odoo
ODOO_URL = os.getenv('ODOO_URL', 'http://odoo:8069')
ODOO_DB = os.getenv('ODOO_DB', 'odoo_production')
ODOO_USER = os.getenv('ODOO_USER', 'admin')
ODOO_PASSWORD = os.getenv('ODOO_PASSWORD', 'admin')

# Configuración SQL Server
SQL_SERVER = os.getenv('SQL_SERVER', 'sqlserver,1433').replace(':1433', ',1433')
SQL_USER = os.getenv('SQL_USER', 'sa')
SQL_PASSWORD = os.getenv('SQL_PASSWORD', 'NestleAdmin@2024')
SQL_DB = os.getenv('SQL_DB', 'nestle_dw')

# ETL Schedule (en minutos)
ETL_SCHEDULE_MINUTES = int(os.getenv('ETL_SCHEDULE_MINUTES', '5'))

# ========================================
# LOGGING
# ========================================

os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/etl.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ========================================
# CONEXIÓN SQL SERVER
# ========================================

class ConexionSQL:
    """Gestiona conexión a SQL Server con reintentos"""

    def __init__(self, max_reintentos=3, timeout=10):
        self.conexion = None
        self.max_reintentos = max_reintentos
        self.timeout = timeout

    def _build_connection_string(self, database: str) -> str:
        # Nota: no incluimos password en logs; solo en el string real
        return (
            # Usar ODBC Driver 18 (instalado en el contenedor).
            f'Driver={{ODBC Driver 18 for SQL Server}};'
            f'Server={SQL_SERVER};'
            f'Database={database};'
            f'UID={SQL_USER};'
            f'PWD={SQL_PASSWORD};'
            f'LoginTimeout=30;'
            f'Connection Timeout=30;'
            # Desactivar por completo negociaciones TLS para evitar timeouts del driver
            # El SQL Server en Docker usa certificado self-signed; forzar encrypt + confiar certificado evita timeouts del ODBC
            f'Encrypt=yes;TrustServerCertificate=yes;'
            f'ConnectionRetryCount=0;'
            f'ApplicationIntent=ReadWrite;'
        )

    def conectar(self):
        """Conecta primero a master y luego a la BD objetivo (mejor diagnóstico)."""
        if pyodbc is None:
            logger.error('pyodbc no instalado')
            return False

        for intento in range(1, self.max_reintentos + 1):
            try:
                logger.info(
                    f'Intento de conexión {intento}/{self.max_reintentos} a SQL Server (validación master -> {SQL_DB})...'
                )

                # 1) Conectar directamente con la BD objetivo, pero validando master primero para diagnóstico.
                # Probamos master con login timeout más corto, y luego BD objetivo.

                master_cs = self._build_connection_string('master')
                logger.info(f"[SQL] Conectando a master. Driver=ODBC Driver 18 for SQL Server, server={SQL_SERVER}, user={SQL_USER}")
                try:
                    cn_master = pyodbc.connect(master_cs, timeout=self.timeout)
                    curm = cn_master.cursor()
                    curm.execute("SELECT @@VERSION")
                    version = curm.fetchone()
                    logger.info(f"✓ Conectado a SQL Server (master): {version[0][:80]}...")

                    # Diagnóstico de BD objetivo (si no existe, la creación se hará luego)
                    curm.execute("SELECT DB_ID(?)", (SQL_DB,))
                    db_id = curm.fetchone()[0]
                    logger.info(f"[SQL] Diagnóstico: DB_ID('{SQL_DB}') = {db_id}")

                    cn_master.close()
                except Exception as e_master:
                    logger.error(f"[SQL] Fallo connect(master): {type(e_master).__name__}: {str(e_master)}")


                objetivo_cs = self._build_connection_string(SQL_DB)
                try:
                    # Usar timeout explícito en connect para que el error sea consistente
                    cn_obj = pyodbc.connect(objetivo_cs, timeout=self.timeout)
                    cur2 = cn_obj.cursor()
                    cur2.execute("SELECT DB_NAME()")
                    db_actual = cur2.fetchone()
                    logger.info(f"✓ Conectado a BD objetivo: {db_actual[0] if db_actual else SQL_DB}")
                    self.conexion = cn_obj
                    return True
                except pyodbc.OperationalError as e_obj:
                    # Intento de auto-reparación en master (dev): crear BD/usuario si faltan
                    logger.warning(
                        f'Conexión directa a DB objetivo falló: {str(e_obj)}. '
                        f'Intentando auto-reparación en master para {SQL_DB}...'
                    )

                    try:
                        cn_master2 = pyodbc.connect(master_cs, timeout=self.timeout)
                        curm2 = cn_master2.cursor()

                        # 1) Crear DB si no existe
                        curm2.execute(
                            f"""
                            IF DB_ID(N'{SQL_DB}') IS NULL
                            BEGIN
                                CREATE DATABASE [{SQL_DB}];
                            END
                            """
                        )

                        # 2) Asegurar que el login sa tenga usuario y pertenezca a db_owner
                        curm2.execute(
                            f"""
                            USE [{SQL_DB}];
                            IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'{SQL_USER}')
                            BEGIN
                                CREATE USER [{SQL_USER}] FOR LOGIN [{SQL_USER}];
                            END

                            DECLARE @role sysname = N'db_owner';
                            IF NOT EXISTS (
                                SELECT 1
                                FROM sys.database_role_members rm
                                JOIN sys.database_principals r ON rm.role_principal_id = r.principal_id
                                JOIN sys.database_principals u ON rm.member_principal_id = u.principal_id
                                WHERE r.name = @role AND u.name = N'{SQL_USER}'
                            )
                            BEGIN
                                EXEC sp_addrolemember @role, N'{SQL_USER}';
                            END
                            """
                        )

                        cn_master2.commit()
                        cn_master2.close()
                        logger.info(f"✓ Auto-reparación completada para {SQL_DB}. Reintentando conexión...")

                        cn_obj2 = pyodbc.connect(objetivo_cs, timeout=self.timeout)
                        self.conexion = cn_obj2
                        return True
                    except Exception as e_fix:
                        logger.error(f'Auto-reparación falló: {str(e_fix)}')
                        raise

                



            except pyodbc.OperationalError as e:
                # Mejor salida de diagnóstico
                logger.error(f'Error conexión (intento {intento}): {str(e)}')

                if intento < self.max_reintentos:
                    espera = intento * 5
                    logger.info(f'Reintentando en {espera} segundos...')
                    time.sleep(espera)
                else:
                    logger.error(
                        f'Fallo conexión a SQL Server después de {self.max_reintentos} intentos. '
                        f'Server={SQL_SERVER} DB={SQL_DB} User={SQL_USER}'
                    )
                    return False

            except Exception as e:
                logger.error(f'Error inesperado en SQL Server: {str(e)}')
                return False

        return False

    
    def ejecutar(self, query, parametros=None):
        """Ejecuta una query (INSERT/UPDATE/DELETE)"""
        try:
            if self.conexion is None:
                raise Exception('Conexión no establecida')
            
            cursor = self.conexion.cursor()
            if parametros:
                cursor.execute(query, parametros)
            else:
                cursor.execute(query)
            
            self.conexion.commit()
            return cursor
            
        except Exception as e:
            logger.error(f'Error ejecutando query: {str(e)}')
            try:
                self.conexion.rollback()
            except:
                pass
            raise
    
    def leer(self, query):
        """Lee datos (SELECT)"""
        try:
            if self.conexion is None:
                raise Exception('Conexión no establecida')
            
            cursor = self.conexion.cursor()
            cursor.execute(query)
            return cursor.fetchall()
            
        except Exception as e:
            logger.error(f'Error leyendo datos: {str(e)}')
            raise
    
    def cerrar(self):
        """Cierra la conexión"""
        if self.conexion:
            try:
                self.conexion.close()
                logger.info('Conexión SQL Server cerrada')
            except:
                pass
            self.conexion = None


# ========================================
# CONEXIÓN ODOO
# ========================================

class ConexionOdoo:
    """Gestiona conexión a Odoo via XML-RPC con reintentos"""
    
    def __init__(self, max_reintentos=3):
        self.url = ODOO_URL
        self.db = ODOO_DB
        self.user = ODOO_USER
        self.password = ODOO_PASSWORD
        self.uid = None
        self.models_proxy = None
        self.max_reintentos = max_reintentos
    
    def conectar(self):
        """Conecta a Odoo con reintentos automáticos"""
        for intento in range(1, self.max_reintentos + 1):
            try:
                logger.info(f'Intento de conexión {intento}/{self.max_reintentos} a Odoo...')
                
                if xmlrpc is None:
                    logger.error('xmlrpc.client no disponible')
                    return False
                
                # Conectar a Odoo
                common_proxy = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
                
                # Autenticar
                self.uid = common_proxy.authenticate(
                    self.db,
                    self.user,
                    self.password,
                    {}
                )
                
                if not self.uid:
                    raise Exception('Autenticación fallida')
                
                # Crear proxy de modelos
                self.models_proxy = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
                
                logger.info(f'✓ Conectado a Odoo - UID: {self.uid}')
                return True
                
            except Exception as e:
                if intento < self.max_reintentos:
                    espera = intento * 5
                    logger.warning(f'Error conexión Odoo (intento {intento}): {str(e)}')
                    logger.info(f'Reintentando en {espera} segundos...')
                    time.sleep(espera)
                else:
                    logger.error(f'Fallo conexión a Odoo después de {self.max_reintentos} intentos')
                    logger.error(str(e))
                    return False
        
        return False
    
    def leer_modelo(self, modelo, campos=None, filtros=None, limite=None):
        """Lee datos de un modelo de Odoo"""
        try:
            if not self.models_proxy or not self.uid:
                raise Exception('No conectado a Odoo')
            
            # Leer IDs
            ids = self.models_proxy.execute_kw(
                self.db, self.uid, self.password,
                modelo, 'search',
                [filtros or []],
                {'limit': limite} if limite else {}
            )
            logger.info(f"IDs encontrados: {len(ids)}")
            
            if not ids:
                logger.info(f'No hay registros en {modelo}')
                return []
            
            # Leer registros
            registros = self.models_proxy.execute_kw(
                self.db, self.uid, self.password,
                modelo, 'read',
                [ids],
                {'fields': campos or []}
            )
            
            logger.info(f'✓ Leídos {len(registros)} registros de {modelo}')
            return registros
            
        except Exception as e:
            logger.error(f'Error leyendo {modelo}: {str(e)}')
            return []


# ========================================
# ETL PROCESOS
# ========================================

class ETLProcess:
    """Orquestador ETL - Nuevo modelo de datos"""
    
    def __init__(self):
        self.sql = ConexionSQL()
        self.odoo = ConexionOdoo()
        self.registros_procesados = {}
        self.errores = []

    @staticmethod
    def _m2o_id(value, default=None):
        """Extrae el ID de un campo many2one de Odoo."""
        if isinstance(value, (list, tuple)) and value:
            return value[0]
        return value or default

    @staticmethod
    def _m2o_name(value, default='General'):
        """Extrae el nombre de un campo many2one de Odoo."""
        if isinstance(value, (list, tuple)) and len(value) > 1:
            return value[1]
        return default
    
    def iniciar(self):
        """Inicia el proceso ETL completo"""
        logger.info('='*70)
        logger.info('INICIANDO PROCESO ETL v2.0')
        logger.info(f'Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        logger.info('='*70)
        
        inicio = datetime.now()
        
        try:
            # Conectar
            if not self.sql.conectar():
                raise Exception('No se pudo conectar a SQL Server')
            
            if not self.odoo.conectar():
                logger.warning('No se pudo conectar a Odoo - continuando offline')
            
            # Ejecutar procesos ETL
            self.cargar_calendarios()
            self.etl_dim_empleado()
            self.etl_dim_geografia()
            self.etl_dim_canal()
            self.etl_dim_producto()
            self.etl_fact_ventas()
            
            # Validaciones
            self.validar_integridad()
            
            # Resumen
            duracion = (datetime.now() - inicio).total_seconds()
            logger.info('='*70)
            logger.info(f'✓ PROCESO ETL COMPLETADO EN {duracion:.1f} segundos')
            logger.info(f'  Registros procesados: {sum(self.registros_procesados.values())}')
            logger.info(f'  Tablas actualizadas: {len(self.registros_procesados)}')
            if self.errores:
                logger.warning(f'  Errores: {len(self.errores)}')
            logger.info('='*70)
            
        except Exception as e:
            logger.error(f'✗ Error fatal en ETL: {str(e)}')
            logger.error(traceback.format_exc())
        
        finally:
            self.sql.cerrar()
    
    def cargar_calendarios(self):
        """Carga la dimensión de tiempo (calendario) si no existe"""
        try:
            logger.info('Verificando dimensión de tiempo...')
            
            # Contar registros existentes
            resultado = self.sql.leer("SELECT COUNT(*) FROM dim_tiempo")
            si_existen = resultado[0][0] if resultado else 0
            
            if si_existen > 0:
                logger.info(f'✓ Calendario ya existe ({si_existen} fechas)')
                return
            
            logger.info('Creando calendario (3 años)...')
            
            inicio = datetime(2024, 1, 1)
            fin = datetime(2026, 12, 31)
            fecha_actual = inicio
            
            contador = 0
            while fecha_actual <= fin:
                try:
                    query = """
                    IF NOT EXISTS (SELECT 1 FROM dim_tiempo WHERE fecha = ?)
                    INSERT INTO dim_tiempo 
                    (fecha, dia, mes, trimestre, anio, nombre_mes, nombre_dia_semana, numero_semana, es_feriado, es_fin_semana)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                    """
                    
                    self.sql.ejecutar(query, [
                        fecha_actual.date(),
                        fecha_actual.date(),
                        fecha_actual.day,
                        fecha_actual.month,
                        (fecha_actual.month - 1) // 3 + 1,
                        fecha_actual.year,
                        fecha_actual.strftime('%B'),
                        fecha_actual.strftime('%A'),
                        fecha_actual.isocalendar()[1],
                        fecha_actual.weekday() >= 5
                    ])
                    
                    contador += 1
                except Exception as e:
                    logger.warning(f'No se pudo cargar fecha {fecha_actual.date()}: {str(e)}')
                
                fecha_actual += timedelta(days=1)
            
            logger.info(f'✓ Calendario cargado: {contador} fechas')
            self.registros_procesados['dim_tiempo'] = contador
            
        except Exception as e:
            logger.error(f'Error cargando calendarios: {str(e)}')
            self.errores.append(f'Calendarios: {str(e)}')
    
    def etl_dim_empleado(self):
        """ETL: Dimensión Empleado desde Odoo"""
        logger.info('ETL: Dimensión Empleado (Vendedores)...')
        
        try:
            # Leer de Odoo
            empleados = self.odoo.leer_modelo(
                'res.users',
                campos=['id', 'name', 'email', 'active'],
                filtros=[['active', '=', True]]
            )
            
            contador = 0
            for emp in empleados:
                try:
                    query = """
                    IF NOT EXISTS (SELECT 1 FROM dim_empleado WHERE id_empleado = ?)
                    INSERT INTO dim_empleado 
                    (id_empleado, nombre_empleado, email_empleado, cargo, departamento, es_activo)
                    VALUES (?, ?, ?, 'Vendedor', 'Ventas', 1)
                    """
                    
                    self.sql.ejecutar(query, [
                        emp.get('id'),
                        emp.get('id'),
                        emp.get('name', 'Sin nombre'),
                        emp.get('email') or ''
                    ])
                    contador += 1
                except Exception as e:
                    logger.warning(f"No se pudo cargar empleado {emp.get('id')}: {str(e)}")
            
            logger.info(f'✓ Empleados cargados: {contador}')
            self.registros_procesados['dim_empleado'] = contador
            
        except Exception as e:
            logger.error(f'Error en dim_empleado: {str(e)}')
            self.errores.append(f'Empleado: {str(e)}')
    
    def etl_dim_geografia(self):
        """ETL: Dimensión Geografía desde Odoo (Clientes)"""
        logger.info('ETL: Dimensión Geografía (Clientes)...')
        
        try:
            # Leer clientes de Odoo
            clientes = self.odoo.leer_modelo(
                'res.partner',
                campos=['id', 'name', 'city', 'state_id', 'country_id', 'phone', 'email'],
                filtros=[['is_company', '=', True]]
            )
            
            contador = 0
            for cliente in clientes:
                try:
                    query = """
                    IF NOT EXISTS (SELECT 1 FROM dim_cliente WHERE id_cliente = ?)
                    INSERT INTO dim_cliente 
                    (id_cliente, nombre_cliente, tipo_cliente, segmento, ciudad, departamento, pais, telefono, email, fecha_registro, es_activo)
                    VALUES (?, ?, 'Distribuidor', 'General', ?, ?, ?, ?, ?, GETDATE(), 1)
                    """
                    
                    self.sql.ejecutar(query, [
                        cliente.get('id'),
                        cliente.get('id'),
                        cliente.get('name', 'Sin nombre'),
                        cliente.get('city') or '',
                        self._m2o_name(cliente.get('state_id'), ''),
                        self._m2o_name(cliente.get('country_id'), ''),
                        cliente.get('phone') or '',
                        cliente.get('email') or ''
                    ])
                    contador += 1
                except Exception as e:
                    logger.warning(f"No se pudo cargar cliente {cliente.get('id')}: {str(e)}")
            
            logger.info(f'✓ Clientes cargados: {contador}')
            self.registros_procesados['dim_cliente'] = contador
            
        except Exception as e:
            logger.error(f'Error en dim_geografia: {str(e)}')
            self.errores.append(f'Geografía: {str(e)}')
    
    def etl_dim_canal(self):
        """ETL: Dimensión Canal (canales de venta)"""
        logger.info('ETL: Dimensión Canal...')
        
        try:
            # Canales de venta predefinidos
            canales = [
                ('Distribuidor', 'Distribuidores mayoristas'),
                ('Minorista', 'Tiendas minoristas'),
                ('Mayorista', 'Clientes mayoristas'),
                ('Online', 'Ventas por internet'),
                ('Directo', 'Ventas directas')
            ]
            
            contador = 0
            for canal in canales:
                try:
                    query = """
                    IF NOT EXISTS (SELECT 1 FROM dim_canal WHERE id_canal = ?)
                    INSERT INTO dim_canal 
                    (id_canal, nombre_canal, descripcion)
                    VALUES (?, ?, ?)
                    """
                    
                    self.sql.ejecutar(query, [
                        canal[0],
                        canal[0],
                        canal[0],
                        canal[1]
                    ])
                    contador += 1
                except Exception as e:
                    logger.warning(f'No se pudo cargar canal {canal[0]}: {str(e)}')
            
            logger.info(f'✓ Canales cargados: {contador}')
            self.registros_procesados['dim_canal'] = contador
            
        except Exception as e:
            logger.error(f'Error en dim_canal: {str(e)}')
            self.errores.append(f'Canal: {str(e)}')
    
    def etl_dim_producto(self):
        """ETL: Dimensión Producto desde Odoo"""
        logger.info('ETL: Dimensión Producto...')
        
        try:
            # Leer productos de Odoo
            productos = self.odoo.leer_modelo(
                'product.product',
                campos=['id', 'name', 'categ_id', 'list_price', 'standard_price'],
                limite=None
            )
            
            contador = 0
            for prod in productos:
                try:
                    precio = float(prod.get('list_price', 0) or 0)
                    costo = float(prod.get('standard_price', 0) or 0)
                    
                    query = """
                    IF NOT EXISTS (SELECT 1 FROM dim_producto WHERE id_producto = ?)
                    INSERT INTO dim_producto 
                    (id_producto, nombre_producto, categoria, SKU, precio_unitario, costo_unitario, margen_ganancia, es_activo)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                    """
                    
                    margen = (precio - costo) / precio * 100 if precio > 0 else 0
                    
                    self.sql.ejecutar(query, [
                        prod.get('id'),
                        prod.get('id'),
                        prod.get('name', 'Sin nombre'),
                        self._m2o_name(prod.get('categ_id'), 'General'),
                        f"SKU{prod.get('id')}",
                        precio,
                        costo,
                        margen
                    ])
                    contador += 1
                except Exception as e:
                    logger.warning(f"No se pudo cargar producto {prod.get('id')}: {str(e)}")
            
            logger.info(f'✓ Productos cargados: {contador}')
            self.registros_procesados['dim_producto'] = contador
            
        except Exception as e:
            logger.error(f'Error en dim_producto: {str(e)}')
            self.errores.append(f'Producto: {str(e)}')
    
    def etl_fact_ventas(self):
        """ETL: Tabla de Hechos de Ventas desde Odoo"""
        logger.info('ETL: Hechos de Ventas...')
        
        try:
            # Leer órdenes de venta
            ordenes = self.odoo.leer_modelo(
                'sale.order',
                campos=['id', 'name', 'partner_id', 'user_id', 'date_order', 'amount_total', 'amount_untaxed', 'order_line'],
                filtros=[['state', 'in', ['sale', 'done']]],
                limite=None
            )
            
            contador = 0
            for orden in ordenes:
                try:
                    lineas = orden.get('order_line') or []
                    linea = {}
                    if lineas and self.odoo.models_proxy:
                        leidas = self.odoo.models_proxy.execute_kw(
                            self.odoo.db, self.odoo.uid, self.odoo.password,
                            'sale.order.line', 'read',
                            [lineas[:1]],
                            {'fields': ['product_id', 'product_uom_qty', 'price_unit', 'discount']}
                        )
                        linea = leidas[0] if leidas else {}

                    monto = float(orden.get('amount_total', 0) or 0)
                    monto_neto = float(orden.get('amount_untaxed', 0) or monto)
                    cantidad = int(float(linea.get('product_uom_qty') or 1))
                    precio_unitario = float(linea.get('price_unit') or (monto_neto / cantidad if cantidad else monto_neto))
                    descuento = float(linea.get('discount') or 0)
                    costo = monto_neto * 0.5
                    ganancia = monto_neto - costo
                    margen = (ganancia / monto_neto * 100) if monto_neto else 0
                    fecha_venta = str(orden.get('date_order') or datetime.now().date())[:10]

                    query = """
                    IF NOT EXISTS (SELECT 1 FROM fact_ventas WHERE id_venta = ?)
                    INSERT INTO fact_ventas 
                    (id_venta, numero_venta, id_cliente, id_empleado, id_producto, id_tiempo, id_canal,
                     cantidad, precio_unitario, monto_venta, descuento, monto_neto, costo_venta, ganancia_bruta,
                     margen_porcentaje, estado, tipo_venta, forma_pago, fecha_venta)
                    VALUES (?, ?, ?, ?, ?,
                            COALESCE((SELECT id_tiempo FROM dim_tiempo WHERE fecha = ?), (SELECT MAX(id_tiempo) FROM dim_tiempo)),
                            'Distribuidor',
                            ?, ?, ?, ?, ?, ?, ?, ?, 'Entregado', 'Normal', 'Credito', ?)
                    """

                    self.sql.ejecutar(query, [
                        orden.get('id'),
                        orden.get('id'),
                        orden.get('name') or f"SO{orden.get('id')}",
                        self._m2o_id(orden.get('partner_id'), 1),
                        self._m2o_id(orden.get('user_id'), 1),
                        self._m2o_id(linea.get('product_id'), 1),
                        fecha_venta,
                        cantidad,
                        precio_unitario,
                        monto,
                        descuento,
                        monto_neto,
                        costo,
                        ganancia,
                        margen,
                        fecha_venta
                    ])
                    contador += 1
                except Exception as e:
                    logger.warning(f"No se pudo cargar venta {orden.get('id')}: {str(e)}")
            
            logger.info(f'✓ Ventas cargadas: {contador}')
            self.registros_procesados['fact_ventas'] = contador
            
        except Exception as e:
            logger.error(f'Error en fact_ventas: {str(e)}')
            self.errores.append(f'Ventas: {str(e)}')
    
    def validar_integridad(self):
        """Valida integridad de datos en Data Warehouse"""
        try:
            logger.info('Validando integridad de datos...')
            
            # Contar registros por tabla
            tablas = [
                'dim_tiempo', 'dim_empleado', 'dim_cliente', 
                'dim_canal', 'dim_producto', 'fact_ventas'
            ]
            
            for tabla in tablas:
                try:
                    resultado = self.sql.leer(f"SELECT COUNT(*) FROM {tabla}")
                    cantidad = resultado[0][0] if resultado else 0
                    logger.info(f'  {tabla}: {cantidad} registros')
                except Exception as e:
                    logger.warning(f'  {tabla}: no accessible ({str(e)})')
            
            logger.info('✓ Validación completada')
            
        except Exception as e:
            logger.warning(f'Error en validación: {str(e)}')


# ========================================
# SCHEDULER
# ========================================

def ejecutar_etl():
    """Ejecuta el proceso ETL completo"""
    etl = ETLProcess()
    etl.iniciar()


def smoke_test_sql():
    """Prueba rápida de conexión SQL para evitar matar el contenedor en carga completa."""
    etl = ETLProcess()
    ok = etl.sql.conectar()
    if ok:
        logger.info('✓ Smoke-test: conexión SQL OK')
    else:
        logger.error('✗ Smoke-test: conexión SQL FAIL')
    etl.sql.cerrar()



def iniciar_scheduler():
    """Inicia el scheduler para ejecutar ETL cada N minutos"""
    logger.info(f'Iniciando Scheduler - Ejecutar cada {ETL_SCHEDULE_MINUTES} minutos')
    
    # Programar ejecución periódica
    schedule.every(ETL_SCHEDULE_MINUTES).minutes.do(ejecutar_etl)
    
    # Ejecutar inmediatamente al iniciar
    logger.info('Ejecutando ETL inicial...')
    ejecutar_etl()
    
    # Loop del scheduler
    logger.info('Scheduler activo - esperando próxima ejecución...')
    while True:
        schedule.run_pending()
        time.sleep(30)  # Revisar cada 30 segundos


# ========================================
# MAIN
# ========================================

if __name__ == '__main__':
    try:
        logger.info('='*70)
        logger.info('SISTEMA ETL NESTLE v2.0 - INICIANDO')
        logger.info('='*70)
        logger.info(f'ODOO_URL: {ODOO_URL}')
        logger.info(f'SQL_SERVER: {SQL_SERVER}')
        logger.info(f'ETL Schedule: cada {ETL_SCHEDULE_MINUTES} minutos')
        logger.info('='*70)
        
        # Smoke-test opcional para diagnosticar arranque (sin correr el ETL completo)
        if '--smoke-test' in sys.argv:
            logger.info('Ejecutando SMOKE TEST SQL...')
            smoke_test_sql()
            sys.exit(0)

        # Iniciar scheduler
        iniciar_scheduler()

        
    except KeyboardInterrupt:
        logger.info('✓ ETL detenido por usuario')
        sys.exit(0)
    except Exception as e:
        logger.error(f'✗ Error fatal: {str(e)}')
        logger.error(traceback.format_exc())
        sys.exit(1)

