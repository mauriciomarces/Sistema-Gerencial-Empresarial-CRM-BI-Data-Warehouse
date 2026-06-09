#!/usr/bin/env python3

import os
import random
import xmlrpc.client

ODOO_URL = os.getenv("ODOO_URL", "http://odoo:8069")
ODOO_DB = os.getenv("ODOO_DB", "odoo_production")
ODOO_USER = os.getenv("ODOO_USER", "admin")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD", "admin")

TOTAL_LEADS = 500

EMPRESAS = [
    "Distribuidora Andina",
    "Comercial Altiplano",
    "Supermercados Bolivia",
    "Retail Express",
    "Mercados Unidos",
    "Grupo Empresarial Oriente",
    "Importadora Nacional",
    "Comercial del Sur",
    "Distribuciones La Paz",
    "MegaMarket"
]

CIUDADES = [
    "La Paz",
    "Cochabamba",
    "Santa Cruz",
    "Oruro",
    "Tarija",
    "Sucre",
    "Potosi",
    "Trinidad",
    "Cobija"
]

CONTACTOS = [
    "Carlos",
    "Maria",
    "Juan",
    "Luis",
    "Ana",
    "Patricia",
    "Roberto",
    "Sergio",
    "Andrea",
    "Fernando"
]


def main():

    common = xmlrpc.client.ServerProxy(
        f"{ODOO_URL}/xmlrpc/2/common"
    )

    uid = common.authenticate(
        ODOO_DB,
        ODOO_USER,
        ODOO_PASSWORD,
        {}
    )

    if not uid:
        print("Error autenticando")
        return

    models = xmlrpc.client.ServerProxy(
        f"{ODOO_URL}/xmlrpc/2/object"
    )

    print("Buscando etapas CRM...")

    stages = models.execute_kw(
        ODOO_DB,
        uid,
        ODOO_PASSWORD,
        "crm.stage",
        "search_read",
        [[]],
        {
            "fields": ["id", "name"]
        }
    )

    if not stages:
        print("No se encontraron etapas CRM")
        return

    print(f"Etapas encontradas: {len(stages)}")

    for i in range(TOTAL_LEADS):

        empresa = random.choice(EMPRESAS)
        ciudad = random.choice(CIUDADES)
        nombre = random.choice(CONTACTOS)

        stage = random.choice(stages)

        monto = random.randint(1000, 50000)

        lead = {
            "name": f"Venta {empresa} #{i+1}",
            "partner_name": empresa,
            "contact_name": nombre,
            "city": ciudad,
            "email_from": f"contacto{i+1}@empresa.com",
            "phone": f"7{random.randint(1000000,9999999)}",
            "expected_revenue": monto,
            "probability": random.choice([10,25,50,75,100]),
            "stage_id": stage["id"],
            "type": "opportunity"
        }

        models.execute_kw(
            ODOO_DB,
            uid,
            ODOO_PASSWORD,
            "crm.lead",
            "create",
            [lead]
        )

        if i % 50 == 0:
            print(f"{i} oportunidades creadas")

    print(f"CRM poblado con {TOTAL_LEADS} oportunidades")


if __name__ == "__main__":
    main()