#!/usr/bin/env python3

import random
import xmlrpc.client
from datetime import datetime, timedelta

ODOO_URL = "http://odoo:8069"
ODOO_DB = "odoo_production"
ODOO_USER = "admin"
ODOO_PASSWORD = "admin"

common = xmlrpc.client.ServerProxy(
    f"{ODOO_URL}/xmlrpc/2/common"
)

uid = common.authenticate(
    ODOO_DB,
    ODOO_USER,
    ODOO_PASSWORD,
    {}
)

models = xmlrpc.client.ServerProxy(
    f"{ODOO_URL}/xmlrpc/2/object"
)

def call(model, method, args=None, kwargs=None):
    return models.execute_kw(
        ODOO_DB,
        uid,
        ODOO_PASSWORD,
        model,
        method,
        args or [],
        kwargs or {}
    )

print("Creando clientes...")

ciudades = [
    "La Paz",
    "Santa Cruz",
    "Cochabamba",
    "Tarija",
    "Sucre",
    "Oruro",
    "Potosi",
    "Trinidad",
    "Cobija"
]

cliente_ids = []

for i in range(1, 501):

    partner_id = call(
        "res.partner",
        "create",
        [{
            "name": f"Distribuidora {i:03}",
            "is_company": True,
            "city": random.choice(ciudades),
            "phone": f"7{random.randint(1000000,9999999)}",
            "email": f"cliente{i}@empresa.com"
        }]
    )

    cliente_ids.append(partner_id)

print("Clientes creados")

productos_base = [
    "Nescafe",
    "Milo",
    "KitKat",
    "Crunch",
    "Nido",
    "Nestum",
    "La Lechera",
    "Dog Chow",
    "Cat Chow",
    "Nesquik"
]

producto_ids = []

print("Creando productos...")

for i in range(1, 101):

    nombre = random.choice(productos_base)

    precio = random.randint(5,80)
    costo = round(precio * random.uniform(0.4,0.7),2)

    product_id = call(
        "product.product",
        "create",
        [{
            "name": f"{nombre} {i}",
            "sale_ok": True,
            "purchase_ok": True,
            "list_price": precio,
            "standard_price": costo
        }]
    )

    producto_ids.append(product_id)

print("Productos creados")

usuarios = call(
    "res.users",
    "search",
    [[]]
)

if not usuarios:
    raise Exception("No existen usuarios")

inicio = datetime(2024,1,1)
fin = datetime(2026,6,1)

dias = (fin - inicio).days

print("Creando ventas...")

for i in range(10000):

    cliente = random.choice(cliente_ids)
    producto = random.choice(producto_ids)
    vendedor = random.choice(usuarios)

    fecha = inicio + timedelta(
        days=random.randint(0,dias)
    )

    cantidad = random.choices(
        [1,2,3,5,10,20],
        weights=[30,25,20,15,7,3]
    )[0]

    precio = random.randint(5,80)

    order_id = call(
        "sale.order",
        "create",
        [{
            "partner_id": cliente,
            "user_id": vendedor,
            "date_order": fecha.strftime("%Y-%m-%d %H:%M:%S"),
            "order_line": [
                (
                    0,
                    0,
                    {
                        "product_id": producto,
                        "product_uom_qty": cantidad,
                        "price_unit": precio
                    }
                )
            ]
        }]
    )

    call(
        "sale.order",
        "action_confirm",
        [[order_id]]
    )

    if i % 500 == 0:
        print(f"{i} ventas creadas")

print("Proceso terminado")