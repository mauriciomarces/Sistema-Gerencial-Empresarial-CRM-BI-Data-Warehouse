-- ========================================
-- CREACIÓN DEL DATA WAREHOUSE NESTLE
-- Database: nestle_dw
-- Modelo: Estrella
-- ========================================

-- Crear base de datos
IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'nestle_dw')
    CREATE DATABASE nestle_dw;
GO

USE nestle_dw;
GO

-- ========================================
-- DIMENSIONES
-- ========================================

-- DIMENSIÓN: CLIENTE
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'dim_cliente')
BEGIN
    CREATE TABLE dim_cliente (
        cliente_id INT PRIMARY KEY IDENTITY(1,1),
        codigo_cliente VARCHAR(20) UNIQUE NOT NULL,
        nombre_cliente VARCHAR(255) NOT NULL,
        tipo_cliente VARCHAR(50), -- Distribuidor, Minorista, Mayorista
        sector VARCHAR(100),
        ciudad VARCHAR(100),
        region VARCHAR(100),
        pais VARCHAR(100),
        telefono VARCHAR(20),
        email VARCHAR(100),
        fecha_registro DATE,
        es_activo BIT DEFAULT 1,
        fecha_creacion DATETIME DEFAULT GETDATE(),
        fecha_modificacion DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX idx_cliente_codigo ON dim_cliente(codigo_cliente);
    CREATE INDEX idx_cliente_ciudad ON dim_cliente(ciudad);
    CREATE INDEX idx_cliente_activo ON dim_cliente(es_activo);
END
GO

-- DIMENSIÓN: PRODUCTO
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'dim_producto')
BEGIN
    CREATE TABLE dim_producto (
        producto_id INT PRIMARY KEY IDENTITY(1,1),
        codigo_producto VARCHAR(50) UNIQUE NOT NULL,
        nombre_producto VARCHAR(255) NOT NULL,
        categoria VARCHAR(100),
        subcategoria VARCHAR(100),
        marca VARCHAR(100),
        presentacion VARCHAR(50), -- 500g, 1kg, etc
        precio_unitario DECIMAL(10,2),
        costo_unitario DECIMAL(10,2),
        margen_ganancia DECIMAL(5,2),
        unidad_medida VARCHAR(20),
        es_activo BIT DEFAULT 1,
        fecha_inicio_venta DATE,
        fecha_creacion DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX idx_producto_codigo ON dim_producto(codigo_producto);
    CREATE INDEX idx_producto_categoria ON dim_producto(categoria);
    CREATE INDEX idx_producto_marca ON dim_producto(marca);
END
GO

-- DIMENSIÓN: TIEMPO (Calendario)
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'dim_tiempo')
BEGIN
    CREATE TABLE dim_tiempo (
        tiempo_id INT PRIMARY KEY IDENTITY(1,1),
        fecha DATE UNIQUE NOT NULL,
        dia INT,
        mes INT,
        trimestre INT,
        anio INT,
        nombre_mes VARCHAR(20),
        nombre_dia_semana VARCHAR(20),
        numero_semana INT,
        es_feriado BIT DEFAULT 0,
        es_fin_semana BIT DEFAULT 0
    );
    
    CREATE INDEX idx_tiempo_fecha ON dim_tiempo(fecha);
    CREATE INDEX idx_tiempo_anio_mes ON dim_tiempo(anio, mes);
END
GO

-- DIMENSIÓN: VENDEDOR
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'dim_vendedor')
BEGIN
    CREATE TABLE dim_vendedor (
        vendedor_id INT PRIMARY KEY IDENTITY(1,1),
        codigo_vendedor VARCHAR(20) UNIQUE NOT NULL,
        nombre_vendedor VARCHAR(255) NOT NULL,
        apellido_vendedor VARCHAR(255),
        email_vendedor VARCHAR(100),
        telefono_vendedor VARCHAR(20),
        zona_asignada VARCHAR(100),
        gerente_id INT,
        fecha_ingreso DATE,
        es_activo BIT DEFAULT 1,
        fecha_creacion DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX idx_vendedor_codigo ON dim_vendedor(codigo_vendedor);
    CREATE INDEX idx_vendedor_zona ON dim_vendedor(zona_asignada);
    CREATE INDEX idx_vendedor_activo ON dim_vendedor(es_activo);
END
GO

-- ========================================
-- TABLA DE HECHOS: VENTAS
-- ========================================
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'fact_ventas')
BEGIN
    CREATE TABLE fact_ventas (
        venta_id INT PRIMARY KEY IDENTITY(1,1),
        numero_pedido VARCHAR(50) UNIQUE NOT NULL,
        cliente_id INT NOT NULL,
        producto_id INT NOT NULL,
        vendedor_id INT NOT NULL,
        tiempo_id INT NOT NULL,
        tiempo_entrega_id INT, -- Fecha de entrega
        
        -- Medidas
        cantidad_unidades INT NOT NULL,
        precio_unitario DECIMAL(10,2) NOT NULL,
        monto_venta DECIMAL(15,2) NOT NULL,
        descuento_aplicado DECIMAL(15,2) DEFAULT 0,
        monto_neto DECIMAL(15,2) NOT NULL,
        costo_productos DECIMAL(15,2) NOT NULL,
        ganancia_bruta DECIMAL(15,2) NOT NULL,
        
        -- Estado
        estado_pedido VARCHAR(50), -- Pendiente, Confirmado, Entregado, Cancelado
        tipo_venta VARCHAR(50), -- Normal, Promoción, etc
        
        -- Auditoría
        fecha_creacion DATETIME DEFAULT GETDATE(),
        fecha_entrega DATETIME,
        
        FOREIGN KEY (cliente_id) REFERENCES dim_cliente(cliente_id),
        FOREIGN KEY (producto_id) REFERENCES dim_producto(producto_id),
        FOREIGN KEY (vendedor_id) REFERENCES dim_vendedor(vendedor_id),
        FOREIGN KEY (tiempo_id) REFERENCES dim_tiempo(tiempo_id)
    );
    
    CREATE INDEX idx_venta_numero ON fact_ventas(numero_pedido);
    CREATE INDEX idx_venta_cliente ON fact_ventas(cliente_id);
    CREATE INDEX idx_venta_producto ON fact_ventas(producto_id);
    CREATE INDEX idx_venta_vendedor ON fact_ventas(vendedor_id);
    CREATE INDEX idx_venta_tiempo ON fact_ventas(tiempo_id);
    CREATE INDEX idx_venta_estado ON fact_ventas(estado_pedido);
END
GO

-- ========================================
-- TABLA AUXILIAR: INVENTARIO
-- ========================================
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'fact_inventario')
BEGIN
    CREATE TABLE fact_inventario (
        inventario_id INT PRIMARY KEY IDENTITY(1,1),
        producto_id INT NOT NULL,
        tiempo_id INT NOT NULL,
        bodega VARCHAR(100),
        cantidad_disponible INT,
        cantidad_reservada INT,
        cantidad_total INT,
        valor_total DECIMAL(15,2),
        rotacion_dias INT,
        fecha_actualizacion DATETIME DEFAULT GETDATE(),
        
        FOREIGN KEY (producto_id) REFERENCES dim_producto(producto_id),
        FOREIGN KEY (tiempo_id) REFERENCES dim_tiempo(tiempo_id)
    );
    
    CREATE INDEX idx_inv_producto ON fact_inventario(producto_id);
    CREATE INDEX idx_inv_tiempo ON fact_inventario(tiempo_id);
END
GO

-- ========================================
-- VISTAS ANALÍTICAS
-- ========================================

-- Vista: Resumen de ventas por cliente
CREATE OR ALTER VIEW vw_ventas_por_cliente AS
SELECT 
    dc.cliente_id,
    dc.nombre_cliente,
    dc.ciudad,
    dc.tipo_cliente,
    COUNT(fv.venta_id) AS total_pedidos,
    SUM(fv.cantidad_unidades) AS total_unidades,
    SUM(fv.monto_neto) AS monto_total,
    SUM(fv.ganancia_bruta) AS ganancia_total,
    AVG(fv.monto_neto) AS promedio_venta
FROM fact_ventas fv
INNER JOIN dim_cliente dc ON fv.cliente_id = dc.cliente_id
GROUP BY dc.cliente_id, dc.nombre_cliente, dc.ciudad, dc.tipo_cliente;
GO

-- Vista: Resumen de ventas por producto
CREATE OR ALTER VIEW vw_ventas_por_producto AS
SELECT 
    dp.producto_id,
    dp.nombre_producto,
    dp.categoria,
    dp.marca,
    COUNT(fv.venta_id) AS total_ventas,
    SUM(fv.cantidad_unidades) AS unidades_vendidas,
    SUM(fv.monto_neto) AS monto_total,
    AVG(fv.precio_unitario) AS precio_promedio,
    SUM(fv.ganancia_bruta) AS ganancia_total
FROM fact_ventas fv
INNER JOIN dim_producto dp ON fv.producto_id = dp.producto_id
GROUP BY dp.producto_id, dp.nombre_producto, dp.categoria, dp.marca;
GO

-- Vista: Desempeño de vendedores
CREATE OR ALTER VIEW vw_desempenio_vendedores AS
SELECT 
    dv.vendedor_id,
    dv.nombre_vendedor,
    dv.zona_asignada,
    COUNT(DISTINCT fv.cliente_id) AS clientes_atendidos,
    COUNT(fv.venta_id) AS total_pedidos,
    SUM(fv.cantidad_unidades) AS total_unidades,
    SUM(fv.monto_neto) AS monto_total,
    SUM(fv.ganancia_bruta) AS ganancia_total,
    AVG(fv.ganancia_bruta) AS ganancia_promedio_pedido
FROM fact_ventas fv
INNER JOIN dim_vendedor dv ON fv.vendedor_id = dv.vendedor_id
GROUP BY dv.vendedor_id, dv.nombre_vendedor, dv.zona_asignada;
GO

-- Vista: Tendencias mensuales
CREATE OR ALTER VIEW vw_ventas_mensuales AS
SELECT 
    YEAR(dt.fecha) AS anio,
    MONTH(dt.fecha) AS mes,
    dt.nombre_mes,
    COUNT(fv.venta_id) AS total_pedidos,
    SUM(fv.cantidad_unidades) AS total_unidades,
    SUM(fv.monto_neto) AS monto_total,
    SUM(fv.ganancia_bruta) AS ganancia_total,
    COUNT(DISTINCT fv.cliente_id) AS clientes_nuevos
FROM fact_ventas fv
INNER JOIN dim_tiempo dt ON fv.tiempo_id = dt.tiempo_id
GROUP BY YEAR(dt.fecha), MONTH(dt.fecha), dt.nombre_mes;
GO

PRINT 'Data Warehouse Nestle creado exitosamente';