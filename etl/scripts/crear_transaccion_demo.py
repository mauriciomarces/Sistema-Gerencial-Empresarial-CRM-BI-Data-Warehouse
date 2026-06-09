#!/usr/bin/env python3
"""Crea una venta demo en Odoo para validar Odoo -> ETL -> SQL Server."""

import os
import sys
import xmlrpc.client


ODOO_URL = os.getenv("ODOO_URL", "http://odoo:8069")
ODOO_DB = os.getenv("ODOO_DB", "odoo_production")
ODOO_USER = os.getenv("ODOO_USER", "admin")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD", "admin")


def main():
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
    if not uid:
        print("No se pudo autenticar en Odoo")
        return 1

    models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")

    def call(model, method, args=None, kwargs=None):
        return models.execute_kw(
            ODOO_DB,
            uid,
            ODOO_PASSWORD,
            model,
            method,
            args or [],
            kwargs or {},
        )

    partner_name = "Cliente Demo BI"
    partner_ids = call("res.partner", "search", [[["name", "=", partner_name]]], {"limit": 1})
    if partner_ids:
        partner_id = partner_ids[0]
    else:
        partner_id = call(
            "res.partner",
            "create",
            [{
                "name": partner_name,
                "is_company": True,
                "city": "La Paz",
                "phone": "70000001",
                "email": "cliente.demo.bi@nestle.local",
            }],
        )

    product_name = "Producto Demo BI"
    product_ids = call("product.product", "search", [[["name", "=", product_name]]], {"limit": 1})
    if product_ids:
        product_id = product_ids[0]
    else:
        product_id = call(
            "product.product",
            "create",
            [{
                "name": product_name,
                "sale_ok": True,
                "purchase_ok": True,
                "list_price": 25.0,
                "standard_price": 12.5,
            }],
        )

    order_id = call(
        "sale.order",
        "create",
        [{
            "partner_id": partner_id,
            "order_line": [
                (0, 0, {
                    "product_id": product_id,
                    "product_uom_qty": 10,
                    "price_unit": 25.0,
                })
            ],
        }],
    )
    call("sale.order", "action_confirm", [[order_id]])

    order = call(
        "sale.order",
        "read",
        [[order_id]],
        {"fields": ["name", "state", "amount_total"]},
    )[0]
    print(
        f"Venta demo creada: {order['name']} | estado={order['state']} | total={order['amount_total']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
