#!/usr/bin/env python3
"""
GENERADOR DE DATOS - Crea datos de demostración en Odoo
Ejecutar este script después de iniciar el sistema

Uso: python generar_datos.py
"""

import xmlrpc.client
import random
import time
from datetime import datetime, timedelta
import sys

# ========================================
# CONFIGURACIÓN
# ========================================

ODOO_URL = 'http://localhost:8069'
ODOO_DB = 'odoo_production'
ODOO_USER = 'admin'
ODOO_PASSWORD = 'admin'

# Esperar a que Odoo esté listo
MAX_INTENTOS = 10
ESPERA_SEGUNDOS = 5

# ========================================
# FUNCIÓN DE CONEXIÓN
# ========================================

def conectar_odoo(intento=1):
    """Conecta a Odoo con reintentos automáticos"""
    if intento > MAX_INTENTOS:
        print("✗ No se pudo conectar a Odoo después de múltiples intentos")
        sys.exit(1)
    
    try:
        print(f"[{intento}/{MAX_INTENTOS}] Conectando a Odoo...")
        
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
        
        if not uid:
            raise Exception("Autenticación fallida")
        
        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
        
        # Test de conexión
        models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'res.partner', 'search', [])
        
        print(f"✓ Conectado a Odoo (UID: {uid})")
        return uid, models
        
    except Exception as e:
        print(f"  Error: {str(e)}")
        if intento < MAX_INTENTOS:
            print(f"  Reintentando en {ESPERA_SEGUNDOS} segundos...")
            time.sleep(ESPERA_SEGUNDOS)
            return conectar_odoo(intento + 1)
        else:
            raise

# ========================================
# CREAR CLIENTES
# ========================================

def crear_clientes(uid, models):
    """Crea 15 clientes de demostración"""
    print("\n" + "="*60)
    print("GENERANDO CLIENTES")
    print("="*60)
    
    ciudades = [
        ('La Paz', 'La Paz', 'Bolivia'),
        ('Cochabamba', 'Cochabamba', 'Bolivia'),
        ('Santa Cruz', 'Santa Cruz', 'Bolivia'),
        ('Tarija', 'Tarija', 'Bolivia'),
        ('Oruro', 'Oruro', 'Bolivia'),
    ]
    
    tipos_cliente = ['Distribuidor', 'Minorista', 'Mayorista']
    
    clientes_ids = []
    
    for i in range(1, 16):
        ciudad, dept, pais = random.choice(ciudades)
        tipo = random.choice(tipos_cliente)
        
        cliente = {
            'name': f'Cliente Corporativo {i:02d}',
            'email': f'cliente{i:02d}@nestlebi.bo',
            'phone': f'7{1000000 + i:07d}',
            'city': ciudad,
            'state_id': 1,
            'country_id': 1,
            'is_company': True,
            'x_studio_tipo_cliente': tipo,
        }
        
        try:
            cliente_id = models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'res.partner', 'create', [cliente]
            )
            clientes_ids.append(cliente_id)
            print(f"  ✓ Cliente {i:02d}: {cliente['name']} ({tipo}) - ID: {cliente_id}")
        except Exception as e:
            print(f"  ✗ Error creando cliente {i}: {str(e)}")
    
    print(f"\n✓ Total clientes creados: {len(clientes_ids)}")
    return clientes_ids

# ========================================
# CREAR PRODUCTOS
# ========================================

def crear_productos(uid, models):
    """Crea 12 productos de demostración"""
    print("\n" + "="*60)
    print("GENERANDO PRODUCTOS")
    print("="*60)
    
    productos_data = [
        ('Nescafé Clásico 200g', 'Café', 45.00, 22.50),
        ('Nestlé Leche Condensada 397g', 'Lácteos', 8.50, 4.25),
        ('Cereal Fitness 375g', 'Cereales', 22.00, 11.00),
        ('Agua Purificada 500ml', 'Bebidas', 2.50, 1.25),
        ('Helado Edy\'s Vainilla 1.5L', 'Congelados', 35.00, 17.50),
        ('Chocolate Aero 100g', 'Confitería', 12.00, 6.00),
        ('Yogur Natural 125g', 'Lácteos', 3.50, 1.75),
        ('Milo Matinal 400g', 'Bebidas', 28.00, 14.00),
        ('Galletas María 200g', 'Pastas', 8.00, 4.00),
        ('Purina Pro Plan 15kg', 'Mascota', 180.00, 90.00),
        ('KitKat 45g', 'Confitería', 5.00, 2.50),
        ('Néctar Maggi 250ml', 'Bebidas', 3.00, 1.50),
    ]
    
    productos_ids = []
    
    for nombre, categoria, precio, costo in productos_data:
        producto = {
            'name': nombre,
            'list_price': precio,
            'standard_price': costo,
            'type': 'product',
            'sale_ok': True,
            'purchase_ok': True,
        }
        
        try:
            prod_id = models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'product.product', 'create', [producto]
            )
            productos_ids.append(prod_id)
            margen = ((precio - costo) / precio * 100) if precio > 0 else 0
            print(f"  ✓ Producto: {nombre}")
            print(f"    Precio: Bs.{precio} | Costo: Bs.{costo} | Margen: {margen:.1f}%")
        except Exception as e:
            print(f"  ✗ Error creando producto: {str(e)}")
    
    print(f"\n✓ Total productos creados: {len(productos_ids)}")
    return productos_ids

# ========================================
# CREAR ÓRDENES DE VENTA
# ========================================

def crear_ordenes_venta(uid, models, clientes_ids, productos_ids):
    """Crea 30 órdenes de venta aleatorias"""
    print("\n" + "="*60)
    print("GENERANDO ÓRDENES DE VENTA")
    print("="*60)
    
    ordenes_ids = []
    
    for i in range(1, 31):
        # Datos aleatorios
        cliente_id = random.choice(clientes_ids)
        num_lineas = random.randint(1, 3)
        fecha = datetime.now() - timedelta(days=random.randint(0, 180))
        
        # Crear líneas de orden
        lineas = []
        monto_total = 0
        
        for _ in range(num_lineas):
            producto_id = random.choice(productos_ids)
            cantidad = random.randint(5, 50)
            
            # Obtener precio del producto
            producto = models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'product.product', 'read', [producto_id], {'fields': ['list_price']}
            )[0]
            
            precio = producto['list_price']
            subtotal = cantidad * precio
            monto_total += subtotal
            
            lineas.append((0, 0, {
                'product_id': producto_id,
                'product_qty': cantidad,
                'price_unit': precio,
            }))
        
        orden = {
            'partner_id': cliente_id,
            'order_line': lineas,
            'date_order': fecha.strftime('%Y-%m-%d'),
        }
        
        try:
            orden_id = models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'sale.order', 'create', [orden]
            )
            
            # Confirmar orden
            models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'sale.order', 'action_confirm', [orden_id]
            )
            
            ordenes_ids.append(orden_id)
            print(f"  ✓ Orden {i:02d}: SO{i:05d} | Monto: Bs.{monto_total:.2f} | {num_lineas} líneas")
            
        except Exception as e:
            print(f"  ✗ Error creando orden {i}: {str(e)}")
    
    print(f"\n✓ Total órdenes creadas: {len(ordenes_ids)}")
    return ordenes_ids

# ========================================
# CREAR CLIENTES ADICIONALES (MASIVO)
# ========================================

def crear_clientes_adicionales(uid, models, cantidad=50):
    """Crea N clientes adicionales para volumen"""
    print("\n" + "="*60)
    print(f"GENERANDO {cantidad} CLIENTES ADICIONALES")
    print("="*60)
    
    ciudades = ['La Paz', 'Cochabamba', 'Santa Cruz', 'Tarija', 'Oruro', 'Sucre', 'Potosí']
    tipos = ['Distribuidor', 'Minorista', 'Mayorista', 'Online']
    
    clientes_ids = []
    
    for i in range(1, cantidad + 1):
        cliente = {
            'name': f'Tienda {i:04d}',
            'email': f'tienda{i:04d}@example.bo',
            'phone': f'7{2000000 + i:07d}',
            'city': random.choice(ciudades),
            'is_company': True,
            'x_studio_tipo_cliente': random.choice(tipos),
        }
        
        try:
            cliente_id = models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'res.partner', 'create', [cliente]
            )
            clientes_ids.append(cliente_id)
            
            if i % 10 == 0:
                print(f"  ✓ {i} clientes creados...")
                
        except Exception as e:
            pass
    
    print(f"✓ Total clientes adicionales: {len(clientes_ids)}")
    return clientes_ids

# ========================================
# MAIN
# ========================================

def main():
    print("="*60)
    print("GENERADOR DE DATOS NESTLE CRM BI v2.0")
    print("="*60)
    
    try:
        # Conectar a Odoo
        uid, models = conectar_odoo()
        
        # Crear datos
        print("\n📊 Iniciando generación de datos de demostración...\n")
        
        clientes_ids = crear_clientes(uid, models)
        productos_ids = crear_productos(uid, models)
        ordenes_ids = crear_ordenes_venta(uid, models, clientes_ids, productos_ids)
        clientes_adicionales = crear_clientes_adicionales(uid, models, 50)
        
        # Resumen
        print("\n" + "="*60)
        print("RESUMEN FINAL")
        print("="*60)
        print(f"✓ Clientes principales: {len(clientes_ids)}")
        print(f"✓ Clientes adicionales: {len(clientes_adicionales)}")
        print(f"✓ Total clientes: {len(clientes_ids) + len(clientes_adicionales)}")
        print(f"✓ Productos: {len(productos_ids)}")
        print(f"✓ Órdenes de venta: {len(ordenes_ids)}")
        print("="*60)
        
        print("\n✓ Datos generados correctamente")
        print("\nEl ETL sincronizará estos datos a SQL Server cada 5 minutos.")
        print("Ver logs: docker-compose logs -f etl-service")
        print("\n¡Sistema listo para demostración!")
        
    except KeyboardInterrupt:
        print("\n✗ Operación cancelada por usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error fatal: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()