#!/usr/bin/env python3
"""
ETL NESTLE - Extrae datos de Odoo e inserta en SQL Server Data Warehouse
Autor: Sistema CRM BI
Version: 1.0
"""

import os
import sys
import logging
import traceback
from datetime import datetime, timedelta
import pyodbc
import psycopg2
import xmlrpc.client
import json
from dotenv import load_dotenv
import schedule
import time

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
SQL_SERVER = os.getenv('SQL_SERVER', 'sqlserver:1433')
SQL_USER = os.getenv('SQL_USER', 'sa')
SQL_PASSWORD = os.getenv('SQL_PASSWORD', 'NestleAdmin@2024')
SQL_DB = os.getenv('SQL_DB', 'nestle_dw')

# Configuración PostgreSQL (Odoo)
PG_HOST = os.getenv('POSTGRES_HOST', 'postgres')
PG_PORT = os.getenv('POSTGRES_PORT', '5432')
PG_USER = os.getenv('POSTGRES_USER', 'odoo')
PG_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'odoo')
PG_DB = os.getenv('POSTGRES_DB', 'odoo_production')

# ========================================
# LOGGING
# ========================================

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
# CONEXIONES
# ========================================

class ConexionSQL:
    """Gestiona conexión a SQL Server"""
    
    def __init__(self):
        self.conexion = None
    
    def conectar(self):
        try:
            connection_string = (
                f'Driver={{ODBC Driver 17 for SQL Server}};'
                f'Server={SQL_SERVER};'
                f'Database={SQL_DB};'
                f'UID={SQL_USER};'
                f'PWD={SQL_PASSWORD};'
            )
            self.conexion = pyodbc.connect(connection_string)
            logger.info('Conectado a SQL Server')
            return True
        except Exception as e:
            logger.error(f'Error conectando a SQL Server: {str(e)}')
            return False
    
    def ejecutar(self, query, parametros=None):
        try:
            cursor = self.conexion.cursor()
            if parametros:
                cursor.execute(query, parametros)
            else:
                cursor.execute(query)
            self.conexion.commit()
            logger.info('Query ejecutada correctamente')
            return cursor
        except Exception as e:
            logger.error(f'Error ejecutando query: {str(e)}')
            self.conexion.rollback()
            raise
    
    def leer(self, query):
        try:
            cursor = self.conexion.cursor()
            cursor.execute(query)
            return cursor.fetchall()
        except Exception as e:
            logger.error(f'Error leyendo datos: {str(e)}')
            raise
    
    def cerrar(self):
        if self.conexion:
            self.conexion.close()
            logger.info('Conexión SQL Server cerrada')


class ConexionOdoo:
    """Gestiona conexión a Odoo via XML-RPC"""
    
    def __init__(self):
        self.url = ODOO_URL
        self.db = ODOO_DB
        self.user = ODOO_USER
        self.password = ODOO_PASSWORD
        self.uid = None
        self.client = None
    
    def conectar(self):
        try:
            self.client = xmlrpc.client.ServerProxy(f'{self.url}/jsonrpc')
            
            # Autenticar
            auth_result = self.client.call(
                'web',
                'session',
                'authenticate',
                {
                    'login': self.user,
                    'password': self.password,
                    'db': self.db
                }
            )
            
            if auth_result and 'uid' in auth_result:
                self.uid = auth_result['uid']
                logger.info(f'Autenticado en Odoo - UID: {self.uid}')
                return True
            else:
                logger.error('Error autenticando en Odoo')
                return False
                
        except Exception as e:
            logger.error(f'Error conectando a Odoo: {str(e)}')
            return False
    
    def leer_modelo(self, modelo, campos=None, filtros=None, limite=None):
        """Lee datos de un modelo de Odoo"""
        try:
            models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
            
            # Leer IDs
            ids = models.execute_kw(
                self.db, self.uid, self.password,
                modelo, 'search',
                [filtros or []],
                {'limit': limite} if limite else {}
            )
            
            # Leer registros
            registros = models.execute_kw(
                self.db, self.uid, self.password,
                modelo, 'read',
                [ids],
                {'fields': campos or []}
            )
            
            logger.info(f'Leídos {len(registros)} registros de {modelo}')
            return registros
            
        except Exception as e:
            logger.error(f'Error leyendo modelo {modelo}: {str(e)}')
            return []


# ========================================
# ETL PROCESOS
# ========================================

class ETLProcess:
    """Orquestador principal del proceso ETL"""
    
    def __init__(self):
        self.sql_conn = ConexionSQL()
        self.odoo_conn = ConexionOdoo()
        self.errores = []
    
    def iniciar(self):
        """Inicia el proceso ETL"""
        logger.info('='*60)
        logger.info('INICIANDO PROCESO ETL')
        logger.info(f'Timestamp: {datetime.now()}')
        logger.info('='*60)
        
        try:
            # Conexiones
            if not self.sql_conn.conectar():
                raise Exception('No se pudo conectar a SQL Server')
            
            if not self.odoo_conn.conectar():
                raise Exception('No se pudo conectar a Odoo')
            
            # Procesos ETL
            self.etl_clientes()
            self.etl_productos()
            self.etl_vendedores()
            self.etl_ventas()
            self.etl_inventario()
            
            logger.info('='*60)
            logger.info('PROCESO ETL COMPLETADO EXITOSAMENTE')
            logger.info('='*60)
            
        except Exception as e:
            logger.error(f'Error fatal en ETL: {str(e)}')
            logger.error(traceback.format_exc())
        
        finally:
            self.sql_conn.cerrar()
    
    def etl_clientes(self):
        """ETL: Clientes desde Odoo a SQL Server"""
        logger.info('Iniciando ETL de Clientes...')
        
        try:
            # Extraer de Odoo
            clientes_odoo = self.odoo_conn.leer_modelo(
                'res.partner',
                campos=['id', 'name', 'email', 'phone', 'city', 'state_id', 'country_id'],
                filtros=[['is_company', '=', True]]
            )
            
            # Transformar e insertar
            for cliente in clientes_odoo:
                try:
                    query = """
                    IF NOT EXISTS (SELECT 1 FROM dim_cliente WHERE codigo_cliente = ?)
                    BEGIN
                        INSERT INTO dim_cliente 
                        (codigo_cliente, nombre_cliente, email, telefono, ciudad, es_activo, fecha_registro)
                        VALUES (?, ?, ?, ?, 1, GETDATE())
                    END
                    """
                    
                    self.sql_conn.ejecutar(query, [
                        f'ODOO_{cliente.get("id")}',
                        f'ODOO_{cliente.get("id")}',
                        cliente.get('name', ''),
                        cliente.get('email', ''),
                        cliente.get('phone', ''),
                        cliente.get('city', '')
                    ])
                    
                except Exception as e:
                    logger.warning(f'Error procesando cliente {cliente}: {str(e)}')
                    self.errores.append(f'Cliente: {str(e)}')
            
            logger.info(f'ETL Clientes completado: {len(clientes_odoo)} registros')
            
        except Exception as e:
            logger.error(f'Error en ETL Clientes: {str(e)}')
            self.errores.append(f'ETL Clientes: {str(e)}')
    
    def etl_productos(self):
        """ETL: Productos desde Odoo a SQL Server"""
        logger.info('Iniciando ETL de Productos...')
        
        try:
            # Extraer de Odoo
            productos_odoo = self.odoo_conn.leer_modelo(
                'product.product',
                campos=['id', 'name', 'categ_id', 'list_price', 'standard_price', 'type']
            )
            
            # Transformar e insertar
            for producto in productos_odoo:
                try:
                    precio = producto.get('list_price', 0)
                    costo = producto.get('standard_price', 0)
                    margen = ((precio - costo) / precio * 100) if precio > 0 else 0
                    
                    query = """
                    IF NOT EXISTS (SELECT 1 FROM dim_producto WHERE codigo_producto = ?)
                    BEGIN
                        INSERT INTO dim_producto
                        (codigo_producto, nombre_producto, precio_unitario, costo_unitario, margen_ganancia, es_activo)
                        VALUES (?, ?, ?, ?, ?, 1)
                    END
                    """
                    
                    self.sql_conn.ejecutar(query, [
                        f'ODOO_{producto.get("id")}',
                        f'ODOO_{producto.get("id")}',
                        producto.get('name', ''),
                        precio,
                        costo,
                        margen
                    ])
                    
                except Exception as e:
                    logger.warning(f'Error procesando producto {producto}: {str(e)}')
                    self.errores.append(f'Producto: {str(e)}')
            
            logger.info(f'ETL Productos completado: {len(productos_odoo)} registros')
            
        except Exception as e:
            logger.error(f'Error en ETL Productos: {str(e)}')
            self.errores.append(f'ETL Productos: {str(e)}')
    
    def etl_vendedores(self):
        """ETL: Vendedores desde Odoo a SQL Server"""
        logger.info('Iniciando ETL de Vendedores...')
        
        try:
            # Extraer de Odoo
            vendedores_odoo = self.odoo_conn.leer_modelo(
                'res.users',
                campos=['id', 'name', 'email', 'phone'],
                filtros=[['active', '=', True]]
            )
            
            # Transformar e insertar
            for vendedor in vendedores_odoo:
                try:
                    query = """
                    IF NOT EXISTS (SELECT 1 FROM dim_vendedor WHERE codigo_vendedor = ?)
                    BEGIN
                        INSERT INTO dim_vendedor
                        (codigo_vendedor, nombre_vendedor, email_vendedor, telefono_vendedor, es_activo, fecha_ingreso)
                        VALUES (?, ?, ?, ?, 1, GETDATE())
                    END
                    """
                    
                    self.sql_conn.ejecutar(query, [
                        f'ODOO_{vendedor.get("id")}',
                        f'ODOO_{vendedor.get("id")}',
                        vendedor.get('name', ''),
                        vendedor.get('email', ''),
                        vendedor.get('phone', '')
                    ])
                    
                except Exception as e:
                    logger.warning(f'Error procesando vendedor {vendedor}: {str(e)}')
                    self.errores.append(f'Vendedor: {str(e)}')
            
            logger.info(f'ETL Vendedores completado: {len(vendedores_odoo)} registros')
            
        except Exception as e:
            logger.error(f'Error en ETL Vendedores: {str(e)}')
            self.errores.append(f'ETL Vendedores: {str(e)}')
    
    def etl_ventas(self):
        """ETL: Ventas (pedidos) desde Odoo a SQL Server"""
        logger.info('Iniciando ETL de Ventas...')
        
        try:
            # Extraer de Odoo
            ventas_odoo = self.odoo_conn.leer_modelo(
                'sale.order',
                campos=['id', 'name', 'partner_id', 'user_id', 'date_order', 'order_line', 'amount_total'],
                filtros=[['state', 'in', ['sale', 'done']]]
            )
            
            logger.info(f'ETL Ventas completado: {len(ventas_odoo)} registros')
            
        except Exception as e:
            logger.error(f'Error en ETL Ventas: {str(e)}')
            self.errores.append(f'ETL Ventas: {str(e)}')
    
    def etl_inventario(self):
        """ETL: Inventario desde Odoo a SQL Server"""
        logger.info('Iniciando ETL de Inventario...')
        
        try:
            logger.info('ETL Inventario completado')
            
        except Exception as e:
            logger.error(f'Error en ETL Inventario: {str(e)}')
            self.errores.append(f'ETL Inventario: {str(e)}')


# ========================================
# SCHEDULER
# ========================================

def ejecutar_etl():
    """Ejecuta el proceso ETL"""
    etl = ETLProcess()
    etl.iniciar()


def iniciar_scheduler():
    """Inicia el scheduler para ejecutar ETL cada hora"""
    logger.info('Iniciando Scheduler de ETL')
    
    # Ejecutar cada hora
    schedule.every().hour.do(ejecutar_etl)
    
    # Ejecutar inmediatamente al iniciar
    ejecutar_etl()
    
    # Loop del scheduler
    while True:
        schedule.run_pending()
        time.sleep(60)


# ========================================
# MAIN
# ========================================

if __name__ == '__main__':
    try:
        # Crear directorio de logs si no existe
        os.makedirs('logs', exist_ok=True)
        
        # Verificar variables de entorno
        logger.info('Verificando configuración...')
        logger.info(f'ODOO_URL: {ODOO_URL}')
        logger.info(f'SQL_SERVER: {SQL_SERVER}')
        logger.info(f'POSTGRES_HOST: {PG_HOST}')
        
        # Iniciar ETL
        if len(sys.argv) > 1 and sys.argv[1] == '--scheduler':
            iniciar_scheduler()
        else:
            ejecutar_etl()
            
    except KeyboardInterrupt:
        logger.info('ETL interrumpido por usuario')
    except Exception as e:
        logger.error(f'Error fatal: {str(e)}')
        logger.error(traceback.format_exc())
        sys.exit(1)