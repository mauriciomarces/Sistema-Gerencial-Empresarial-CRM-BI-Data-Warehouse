USE nestle_dw;
GO

-- ========================================
-- INSERTAR DATOS DE EJEMPLO
-- ========================================

-- 1. DIMENSIÓN TIEMPO (Últimos 2 años)
DECLARE @FechaInicio DATE = '2023-01-01'
DECLARE @FechaFin DATE = GETDATE()
DECLARE @FechaActual DATE = @FechaInicio

WHILE @FechaActual <= @FechaFin
BEGIN
    IF NOT EXISTS (SELECT 1 FROM dim_tiempo WHERE fecha = @FechaActual)
    BEGIN
        INSERT INTO dim_tiempo (
            fecha, dia, mes, trimestre, anio, nombre_mes, nombre_dia_semana,
            numero_semana, es_feriado, es_fin_semana
        )
        VALUES (
            @FechaActual,
            DAY(@FechaActual),
            MONTH(@FechaActual),
            CEILING(MONTH(@FechaActual) / 3.0),
            YEAR(@FechaActual),
            FORMAT(@FechaActual, 'MMMM', 'es-ES'),
            FORMAT(@FechaActual, 'dddd', 'es-ES'),
            DATEPART(WEEK, @FechaActual),
            CASE WHEN MONTH(@FechaActual) = 12 AND DAY(@FechaActual) = 25 THEN 1 ELSE 0 END,
            CASE WHEN DATEPART(WEEKDAY, @FechaActual) IN (1, 7) THEN 1 ELSE 0 END
        );
    END
    SET @FechaActual = DATEADD(DAY, 1, @FechaActual);
END
GO

-- 2. DIMENSIÓN CLIENTE
INSERT INTO dim_cliente (codigo_cliente, nombre_cliente, tipo_cliente, sector, ciudad, region, pais, telefono, email, fecha_registro, es_activo)
VALUES 
    ('CLI001', 'Distribuidora Central Coca-Cola', 'Distribuidor', 'Bebidas', 'La Paz', 'La Paz', 'Bolivia', '2-2123456', 'distribuidor@cocacola.bo', '2023-01-15', 1),
    ('CLI002', 'Supermercado El Corte Inglés', 'Minorista', 'Retail', 'La Paz', 'La Paz', 'Bolivia', '2-2234567', 'compras@elcorte.bo', '2023-02-01', 1),
    ('CLI003', 'Bodega Central Tarija', 'Mayorista', 'Distribución', 'Tarija', 'Tarija', 'Bolivia', '4-6123456', 'bodega@tarija.bo', '2023-03-10', 1),
    ('CLI004', 'Minimarket Don Juan', 'Minorista', 'Retail', 'Cochabamba', 'Cochabamba', 'Bolivia', '4-4234567', 'donjuan@email.bo', '2023-04-05', 1),
    ('CLI005', 'Distribuidora Santa Cruz', 'Distribuidor', 'Bebidas', 'Santa Cruz', 'Santa Cruz', 'Bolivia', '3-3345678', 'distribuidora@santacruz.bo', '2023-05-12', 1),
    ('CLI006', 'Tienda Naturista Salud', 'Minorista', 'Alimentos', 'La Paz', 'La Paz', 'Bolivia', '2-2445678', 'naturista@salud.bo', '2023-06-20', 1),
    ('CLI007', 'Empresa Hogar & Limpieza', 'Mayorista', 'Distribución', 'La Paz', 'La Paz', 'Bolivia', '2-2556789', 'hogar@limpieza.bo', '2023-07-08', 1),
    ('CLI008', 'Supermercado Mega Center', 'Minorista', 'Retail', 'La Paz', 'La Paz', 'Bolivia', '2-2667890', 'mega@center.bo', '2023-08-15', 1),
    ('CLI009', 'Distribuidora Premium Bolivia', 'Distribuidor', 'Premium', 'La Paz', 'La Paz', 'Bolivia', '2-2778901', 'premium@bolivia.bo', '2023-09-22', 1),
    ('CLI010', 'Hotel Boutique Plaza Mayor', 'Mayorista', 'Hotelería', 'La Paz', 'La Paz', 'Bolivia', '2-2889012', 'compras@plazamayor.bo', '2023-10-30', 1);
GO

-- 3. DIMENSIÓN PRODUCTO
INSERT INTO dim_producto (codigo_producto, nombre_producto, categoria, subcategoria, marca, presentacion, precio_unitario, costo_unitario, margen_ganancia, unidad_medida, es_activo, fecha_inicio_venta)
VALUES 
    ('PRD001', 'Nescafé Clásico', 'Bebidas', 'Café', 'Nescafé', '200g', 45.00, 22.50, 50.00, 'UND', 1, '2023-01-01'),
    ('PRD002', 'Nestlé Leche Condensada', 'Lácteos', 'Leche', 'Nestlé', '397g', 8.50, 4.25, 50.00, 'LATA', 1, '2023-01-01'),
    ('PRD003', 'Cereal Fitness', 'Cereales', 'Desayuno', 'Nestlé', '375g', 22.00, 11.00, 50.00, 'CAJA', 1, '2023-01-01'),
    ('PRD004', 'Agua Purificada Nestlé', 'Bebidas', 'Agua', 'Nestlé', '500ml', 2.50, 1.25, 50.00, 'BOTELLA', 1, '2023-01-01'),
    ('PRD005', 'Helado Edy''s Vainilla', 'Congelados', 'Helados', 'Edy''s', '1.5L', 35.00, 17.50, 50.00, 'POTE', 1, '2023-02-01'),
    ('PRD006', 'Chocolate Aero', 'Confitería', 'Chocolate', 'Aero', '100g', 12.00, 6.00, 50.00, 'BARRA', 1, '2023-02-01'),
    ('PRD007', 'Yogur Natural', 'Lácteos', 'Yogur', 'Nestlé', '125g', 3.50, 1.75, 50.00, 'VASO', 1, '2023-03-01'),
    ('PRD008', 'Milo Matinal', 'Bebidas', 'Chocolatada', 'Milo', '400g', 28.00, 14.00, 50.00, 'LATA', 1, '2023-03-01'),
    ('PRD009', 'Galletas María', 'Pastas', 'Galletas', 'Nestlé', '200g', 8.00, 4.00, 50.00, 'CAJA', 1, '2023-04-01'),
    ('PRD010', 'Purina Pro Plan', 'Mascota', 'Alimento Perro', 'Purina', '15kg', 180.00, 90.00, 50.00, 'BOLSA', 1, '2023-04-01');
GO

-- 4. DIMENSIÓN VENDEDOR
INSERT INTO dim_vendedor (codigo_vendedor, nombre_vendedor, apellido_vendedor, email_vendedor, telefono_vendedor, zona_asignada, gerente_id, fecha_ingreso, es_activo)
VALUES 
    ('VND001', 'Carlos', 'López Ramírez', 'carlos.lopez@nestle.bo', '71234567', 'Centro La Paz', NULL, '2023-01-10', 1),
    ('VND002', 'María', 'García Flores', 'maria.garcia@nestle.bo', '72345678', 'Zona Norte', 1, '2023-01-15', 1),
    ('VND003', 'Juan', 'Martínez Silva', 'juan.martinez@nestle.bo', '73456789', 'Zona Sur', 1, '2023-02-01', 1),
    ('VND004', 'Patricia', 'Rodríguez López', 'patricia.rodriguez@nestle.bo', '74567890', 'Cochabamba', 1, '2023-02-15', 1),
    ('VND005', 'Roberto', 'Fernández Díaz', 'roberto.fernandez@nestle.bo', '75678901', 'Santa Cruz', 1, '2023-03-01', 1),
    ('VND006', 'Ana', 'Sánchez Morales', 'ana.sanchez@nestle.bo', '76789012', 'Tarija', NULL, '2023-03-15', 1),
    ('VND007', 'Luis', 'Vega Huanca', 'luis.vega@nestle.bo', '77890123', 'Oruro', NULL, '2023-04-01', 1),
    ('VND008', 'Claudia', 'Quispe Inti', 'claudia.quispe@nestle.bo', '78901234', 'Potosí', 6, '2023-04-15', 1);
GO

-- 5. INSERTAR VENTAS HISTÓRICAS
DECLARE @ClienteID INT, @ProductoID INT, @VendedorID INT, @TiempoID INT, @FechaVenta DATE
DECLARE @Contador INT = 1
DECLARE @CantidadVentas INT = 150

WHILE @Contador <= @CantidadVentas
BEGIN
    SET @ClienteID = (SELECT TOP 1 cliente_id FROM dim_cliente ORDER BY NEWID())
    SET @ProductoID = (SELECT TOP 1 producto_id FROM dim_producto ORDER BY NEWID())
    SET @VendedorID = (SELECT TOP 1 vendedor_id FROM dim_vendedor ORDER BY NEWID())
    SET @FechaVenta = DATEADD(DAY, -(@CantidadVentas - @Contador), GETDATE())
    SET @TiempoID = (SELECT TOP 1 tiempo_id FROM dim_tiempo WHERE fecha = CAST(@FechaVenta AS DATE))
    
    IF @TiempoID IS NOT NULL
    BEGIN
        DECLARE @Cantidad INT = RAND() * 100 + 1
        DECLARE @Precio DECIMAL(10,2) = (SELECT precio_unitario FROM dim_producto WHERE producto_id = @ProductoID)
        DECLARE @Costo DECIMAL(10,2) = (SELECT costo_unitario FROM dim_producto WHERE producto_id = @ProductoID)
        DECLARE @Descuento DECIMAL(15,2) = RAND() * 50
        DECLARE @Monto DECIMAL(15,2) = @Cantidad * @Precio
        DECLARE @MontoNeto DECIMAL(15,2) = @Monto - @Descuento
        DECLARE @Ganancia DECIMAL(15,2) = (@Cantidad * (@Precio - @Costo)) - @Descuento
        
        INSERT INTO fact_ventas (
            numero_pedido, cliente_id, producto_id, vendedor_id, tiempo_id,
            cantidad_unidades, precio_unitario, monto_venta, descuento_aplicado,
            monto_neto, costo_productos, ganancia_bruta, estado_pedido, tipo_venta, fecha_entrega
        )
        VALUES (
            'PED' + FORMAT(@Contador, '0000000'),
            @ClienteID, @ProductoID, @VendedorID, @TiempoID,
            @Cantidad, @Precio, @Monto, @Descuento,
            @MontoNeto, @Cantidad * @Costo, @Ganancia, 'Entregado', 'Normal',
            DATEADD(DAY, RAND() * 15, @FechaVenta)
        )
    END
    
    SET @Contador = @Contador + 1
END
GO

-- 6. INSERTAR DATOS DE INVENTARIO
INSERT INTO fact_inventario (producto_id, tiempo_id, bodega, cantidad_disponible, cantidad_reservada, cantidad_total, valor_total, rotacion_dias)
SELECT 
    p.producto_id,
    (SELECT MAX(tiempo_id) FROM dim_tiempo),
    'Bodega Central La Paz',
    ABS(CHECKSUM(NEWID())) % 500 + 100,
    ABS(CHECKSUM(NEWID())) % 100 + 10,
    ABS(CHECKSUM(NEWID())) % 500 + 100,
    (ABS(CHECKSUM(NEWID())) % 500 + 100) * p.precio_unitario,
    ABS(CHECKSUM(NEWID())) % 30 + 5
FROM dim_producto p
GO

PRINT 'Datos de ejemplo insertados exitosamente'
PRINT 'Total de registros en fact_ventas: ' + CAST((SELECT COUNT(*) FROM fact_ventas) AS VARCHAR)