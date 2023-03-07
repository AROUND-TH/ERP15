# -*- coding: utf-8 -*-
# Copyright (c) Open Value All Rights Reserved

{
    "name": "Purchase Monitor",
    "summary": 'Purchase Monitor',
    "version": "15.0.1.0",
    "category": "Inventory/Purchase",
    "website": 'www.openvalue.cloud',
    "author": "OpenValue",
    "support": 'info@openvalue.cloud',
    "license": "Other proprietary",
    "price": 200.00,
    "currency": 'EUR',
    "depends": [
        "purchase_stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/purchase_views.xml",
        "views/purchase_order_line_history_views.xml",
        "views/purchase_quantity_monitor_views.xml",
        "views/purchase_amount_monitor_views.xml",
    ],
    "application": False,
    "installable": True,
    "auto_install": False,
    "images": ['static/description/banner.png'],
}
