-- ========================================
-- PostgreSQL Init Script para Odoo
-- ========================================

-- Crear extensiones necesarias
CREATE EXTENSION IF NOT EXISTS plpgsql;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Crear rol si no existe
DO
$$BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'odoo') THEN
    CREATE ROLE odoo WITH LOGIN PASSWORD 'odoo' CREATEDB;
  END IF;
END
$$;

-- Asignar permisos
ALTER ROLE odoo CREATEDB;
ALTER ROLE odoo SUPERUSER;

-- PostgreSQL inicializado para Odoo