# -*- coding: utf-8 -*-
# Copyright (c) OpenValue All Rights Reserved

{
    "name": "Stock Location Quantity Overview",
    "summary": "Internal stock location quantity overview",
    "version": "15.0.1.0",
    "category": "Inventory",
    "website": "www.openvalue.cloud",
    "author": "OpenValue",
    "support": "info@openvalue.cloud",
    "license": "Other proprietary",
    "price": 0.00,
    "currency": 'EUR',
    "depends": [
        "stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/stock_location_quantity_overview.xml",
    ],
    "application": False,
    "installable": True,
    "auto_install": False,
    "images": ['static/description/banner.png'],
}
