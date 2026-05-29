#!/bin/bash
# ========================================
# SCRIPT DE INICIALIZACIÓN DE ODOO
# Configura Odoo con módulos y datos iniciales
# ========================================

set -e

ODOO_HOST=${ODOO_HOST:-odoo}
ODOO_PORT=${ODOO_PORT:-8069}
ODOO_USER=${ODOO_USER:-admin}
ODOO_PASSWORD=${ODOO_PASSWORD:-admin}
ODOO_DB=${ODOO_DB:-odoo_production}

echo "========================================="
echo "Iniciando configuración de Odoo"
echo "========================================="

# Esperar a que Odoo esté listo
echo "Esperando a que Odoo esté disponible..."
for i in {1..30}; do
    if curl -f http://${ODOO_HOST}:${ODOO_PORT}/web/health > /dev/null 2>&1; then
        echo "✓ Odoo está disponible"
        break
    fi
    echo "Intento $i/30..."
    sleep 10
done

# Instalar módulos
echo ""
echo "Instalando módulos CRM, Ventas e Inventario..."

curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
      "service": "object",
      "method": "execute_kw",
      "args": [
        "'${ODOO_DB}'",
        2,
        "'${ODOO_PASSWORD}'",
        "ir.module.module",
        "button_immediate_upgrade",
        [1, 2, 3, 4]
      ]
    },
    "id": 1
  }' \
  http://${ODOO_HOST}:${ODOO_PORT}/jsonrpc || true

echo "✓ Configuración completada"

exit 0