-- ========================================
-- CREACIÓN DEL DATA WAREHOUSE NESTLE v2.0
-- Modelo: Estrella mejorado (5 dimensiones + 1 hecho)
-- ========================================

-- Crear base de datos
IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'nestle_dw')
    CREATE DATABASE nestle_dw;
GO

USE nestle_dw;
GO

-- ========================================
-- DIMENSIÓN 1: PRODUCTO
-- ========================================
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'dim_producto')
BEGIN
    CREATE TABLE dim_producto (
        id_producto INT PRIMARY KEY,
        nombre_producto VARCHAR(255) NOT NULL,
        SKU VARCHAR(50) UNIQUE,
        categoria VARCHAR(100),
        marca VARCHAR(100),
        presentacion VARCHAR(50),
        precio_unitario DECIMAL(10,2),
        costo_unitario DECIMAL(10,2),
        margen_ganancia DECIMAL(5,2),
        linea_negocio VARCHAR(100),
        es_activo BIT DEFAULT 1,
        fecha_creacion DATETIME DEFAULT GETDATE(),
        fecha_modificacion DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX idx_prod_sku ON dim_producto(SKU);
    CREATE INDEX idx_prod_categoria ON dim_producto(categoria);
    CREATE INDEX idx_prod_marca ON dim_producto(marca);
END
GO

-- ========================================
-- DIMENSIÓN 2: TIEMPO
-- ========================================
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'dim_tiempo')
BEGIN
    CREATE TABLE dim_tiempo (
        id_tiempo INT PRIMARY KEY IDENTITY(1,1),
        fecha DATE UNIQUE NOT NULL,
        dia INT,
        mes INT,
        trimestre INT,
        anio INT,
        nombre_mes VARCHAR(20),
        nombre_dia_semana VARCHAR(20),
        numero_semana INT,
        numero_dia_anio INT,
        es_feriado BIT DEFAULT 0,
        es_fin_semana BIT DEFAULT 0,
        fecha_creacion DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX idx_tiempo_fecha ON dim_tiempo(fecha);
    CREATE INDEX idx_tiempo_anio_mes ON dim_tiempo(anio, mes);
END
GO

-- ========================================
-- DIMENSIÓN 3: GEOGRAFÍA (CLIENTE)
-- ========================================
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'dim_cliente')
BEGIN
    CREATE TABLE dim_cliente (
        id_cliente INT PRIMARY KEY,
        nombre_cliente VARCHAR(255) NOT NULL,
        tipo_cliente VARCHAR(50),      -- Distribuidor, Minorista, Mayorista
        segmento VARCHAR(100),          -- Premium, Estándar, Básico
        ciudad VARCHAR(100),
        departamento VARCHAR(100),
        region VARCHAR(100),
        pais VARCHAR(100),
        zona_geografica VARCHAR(100),
        telefono VARCHAR(20),
        email VARCHAR(100),
        contacto_principal VARCHAR(100),
        fecha_registro DATE,
        es_activo BIT DEFAULT 1,
        volumen_anual DECIMAL(15,2) DEFAULT 0,
        fecha_creacion DATETIME DEFAULT GETDATE(),
        fecha_modificacion DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX idx_cliente_ciudad ON dim_cliente(ciudad);
    CREATE INDEX idx_cliente_tipo ON dim_cliente(tipo_cliente);
    CREATE INDEX idx_cliente_segmento ON dim_cliente(segmento);
    CREATE INDEX idx_cliente_activo ON dim_cliente(es_activo);
END
GO

-- ========================================
-- DIMENSIÓN 4: CANAL DE VENTA
-- ========================================
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'dim_canal')
BEGIN
    CREATE TABLE dim_canal (
        id_canal VARCHAR(50) PRIMARY KEY,
        nombre_canal VARCHAR(100) UNIQUE NOT NULL,
        descripcion VARCHAR(500),
        tipo_canal VARCHAR(50),        -- Directo, Indirecto, Online
        categoria VARCHAR(100),
        margen_promedio DECIMAL(5,2),
        es_activo BIT DEFAULT 1,
        fecha_creacion DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX idx_canal_nombre ON dim_canal(nombre_canal);
    CREATE INDEX idx_canal_tipo ON dim_canal(tipo_canal);
END
GO

-- ========================================
-- DIMENSIÓN 5: EMPLEADO/VENDEDOR
-- ========================================
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'dim_empleado')
BEGIN
    CREATE TABLE dim_empleado (
        id_empleado INT PRIMARY KEY,
        nombre_empleado VARCHAR(255) NOT NULL,
        apellido_empleado VARCHAR(255),
        email_empleado VARCHAR(100),
        telefono_empleado VARCHAR(20),
        cargo VARCHAR(100),            -- Vendedor, Gerente, Ejecutivo
        departamento VARCHAR(100),     -- Ventas, Marketing, Gerencia
        zona_asignada VARCHAR(100),
        gerente_id INT,
        fecha_ingreso DATE,
        comision_porcentaje DECIMAL(5,2),
        es_activo BIT DEFAULT 1,
        fecha_creacion DATETIME DEFAULT GETDATE(),
        fecha_modificacion DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX idx_empleado_cargo ON dim_empleado(cargo);
    CREATE INDEX idx_empleado_zona ON dim_empleado(zona_asignada);
    CREATE INDEX idx_empleado_activo ON dim_empleado(es_activo);
END
GO

-- ========================================
-- TABLA DE HECHOS: VENTAS
-- ========================================
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'fact_ventas')
BEGIN
    CREATE TABLE fact_ventas (
        id_venta INT PRIMARY KEY,
        numero_venta VARCHAR(50) UNIQUE NOT NULL,
        id_producto INT NOT NULL,
        id_tiempo INT NOT NULL,
        id_cliente INT NOT NULL,
        id_canal VARCHAR(50) NOT NULL,
        id_empleado INT NOT NULL,
        
        -- Medidas cuantitativas
        cantidad INT NOT NULL,
        precio_unitario DECIMAL(10,2) NOT NULL,
        monto_venta DECIMAL(15,2) NOT NULL,
        descuento DECIMAL(15,2) DEFAULT 0,
        monto_neto DECIMAL(15,2) NOT NULL,
        costo_venta DECIMAL(15,2) NOT NULL,
        ganancia_bruta DECIMAL(15,2) NOT NULL,
        margen_porcentaje DECIMAL(5,2),
        
        -- Dimensiones de texto
        estado VARCHAR(50),            -- Entregado, Pendiente, Cancelado
        tipo_venta VARCHAR(50),        -- Normal, Promoción, Mayoreo
        forma_pago VARCHAR(50),        -- Contado, Crédito, Cheque
        
        -- Auditoria
        fecha_venta DATE NOT NULL,
        fecha_entrega DATE,
        fecha_creacion DATETIME DEFAULT GETDATE(),
        fecha_actualizacion DATETIME DEFAULT GETDATE(),
        
        FOREIGN KEY (id_producto) REFERENCES dim_producto(id_producto),
        FOREIGN KEY (id_tiempo) REFERENCES dim_tiempo(id_tiempo),
        FOREIGN KEY (id_cliente) REFERENCES dim_cliente(id_cliente),
        FOREIGN KEY (id_canal) REFERENCES dim_canal(id_canal),
        FOREIGN KEY (id_empleado) REFERENCES dim_empleado(id_empleado)
    );
    
    -- Índices para performance
    CREATE INDEX idx_venta_numero ON fact_ventas(numero_venta);
    CREATE INDEX idx_venta_fecha ON fact_ventas(fecha_venta);
    CREATE INDEX idx_venta_cliente ON fact_ventas(id_cliente);
    CREATE INDEX idx_venta_producto ON fact_ventas(id_producto);
    CREATE INDEX idx_venta_empleado ON fact_ventas(id_empleado);
    CREATE INDEX idx_venta_canal ON fact_ventas(id_canal);
    CREATE INDEX idx_venta_estado ON fact_ventas(estado);
END
GO

-- ========================================
-- VISTAS ANALÍTICAS
-- ========================================

-- Vista: Resumen de ventas por cliente
CREATE OR ALTER VIEW vw_ventas_por_cliente AS
SELECT 
    dc.id_cliente,
    dc.nombre_cliente,
    dc.tipo_cliente,
    dc.ciudad,
    COUNT(fv.id_venta) AS total_pedidos,
    SUM(fv.cantidad) AS total_unidades,
    SUM(fv.monto_neto) AS monto_total,
    AVG(fv.monto_neto) AS promedio_venta,
    SUM(fv.ganancia_bruta) AS ganancia_total,
    MAX(fv.fecha_venta) AS ultima_compra
FROM fact_ventas fv
INNER JOIN dim_cliente dc ON fv.id_cliente = dc.id_cliente
GROUP BY dc.id_cliente, dc.nombre_cliente, dc.tipo_cliente, dc.ciudad;
GO

-- Vista: Resumen de ventas por producto
CREATE OR ALTER VIEW vw_ventas_por_producto AS
SELECT 
    dp.id_producto,
    dp.nombre_producto,
    dp.categoria,
    dp.marca,
    COUNT(fv.id_venta) AS total_ventas,
    SUM(fv.cantidad) AS unidades_vendidas,
    SUM(fv.monto_neto) AS monto_total,
    AVG(fv.precio_unitario) AS precio_promedio,
    SUM(fv.ganancia_bruta) AS ganancia_total,
    AVG(fv.margen_porcentaje) AS margen_promedio
FROM fact_ventas fv
INNER JOIN dim_producto dp ON fv.id_producto = dp.id_producto
GROUP BY dp.id_producto, dp.nombre_producto, dp.categoria, dp.marca;
GO

-- Vista: Desempeño de vendedores
CREATE OR ALTER VIEW vw_desempenio_vendedores AS
SELECT 
    de.id_empleado,
    de.nombre_empleado,
    de.cargo,
    de.zona_asignada,
    COUNT(DISTINCT fv.id_cliente) AS clientes_atendidos,
    COUNT(fv.id_venta) AS total_pedidos,
    SUM(fv.cantidad) AS total_unidades,
    SUM(fv.monto_neto) AS monto_total,
    AVG(fv.monto_neto) AS promedio_venta,
    SUM(fv.ganancia_bruta) AS ganancia_total
FROM fact_ventas fv
INNER JOIN dim_empleado de ON fv.id_empleado = de.id_empleado
GROUP BY de.id_empleado, de.nombre_empleado, de.cargo, de.zona_asignada;
GO

-- Vista: Tendencias mensuales
CREATE OR ALTER VIEW vw_ventas_mensuales AS
SELECT 
    dt.anio,
    dt.mes,
    dt.nombre_mes,
    COUNT(fv.id_venta) AS total_pedidos,
    SUM(fv.cantidad) AS total_unidades,
    SUM(fv.monto_neto) AS monto_total,
    SUM(fv.ganancia_bruta) AS ganancia_total,
    COUNT(DISTINCT fv.id_cliente) AS clientes_unicos,
    AVG(fv.margen_porcentaje) AS margen_promedio
FROM fact_ventas fv
INNER JOIN dim_tiempo dt ON fv.id_tiempo = dt.id_tiempo
GROUP BY dt.anio, dt.mes, dt.nombre_mes;
GO

-- Vista: Ventas por canal
CREATE OR ALTER VIEW vw_ventas_por_canal AS
SELECT 
    dc.nombre_canal,
    dc.tipo_canal,
    COUNT(fv.id_venta) AS total_ventas,
    SUM(fv.cantidad) AS total_unidades,
    SUM(fv.monto_neto) AS monto_total,
    SUM(fv.ganancia_bruta) AS ganancia_total,
    AVG(fv.margen_porcentaje) AS margen_promedio,
    COUNT(DISTINCT fv.id_cliente) AS clientes_unicos
FROM fact_ventas fv
INNER JOIN dim_canal dc ON fv.id_canal = dc.id_canal
GROUP BY dc.nombre_canal, dc.tipo_canal;
GO

-- Vista: Matriz de productos por canal
CREATE OR ALTER VIEW vw_matriz_productos_canal AS
SELECT 
    dp.nombre_producto,
    dc.nombre_canal,
    SUM(fv.cantidad) AS unidades_vendidas,
    SUM(fv.monto_neto) AS monto_total,
    COUNT(fv.id_venta) AS numero_transacciones
FROM fact_ventas fv
INNER JOIN dim_producto dp ON fv.id_producto = dp.id_producto
INNER JOIN dim_canal dc ON fv.id_canal = dc.id_canal
GROUP BY dp.nombre_producto, dc.nombre_canal;
GO

PRINT '✓ Data Warehouse Nestle v2.0 creado exitosamente';
PRINT '  Dimensiones: 5 (Producto, Tiempo, Cliente, Canal, Empleado)';
PRINT '  Hechos: 1 (Ventas)';
PRINT '  Vistas: 6 (analíticas)';
GO
