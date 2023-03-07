# -*- coding: utf-8 -*-
{
    "name": "Separate Quotation No.",
    "author": "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "version": "15.0.1",
    "license": "OPL-1",
    "category": "Sales",
    "summary": """
separate quotation number,
seperate sale order number,
seperate sales order,
separate quotations app,
partition of sales order,
disjoint so module odoo
""",
    "description": """
Separate Quotation No. So easy to manage quotation and sale order no.
separate quotations app, partition of sales order, disjoint so module odoo
""",
    "depends": ["sale_management"],
    "data": [
        "data/sale_quotation.xml",
        "views/sale_order.xml",
        "reports/sale_order_report.xml",
    ],
    "images": ["static/description/background.png", ],
    "auto_install": False,
    "installable": True,
    "application": True,
    "price": 15,
    "currency": "EUR"
}
