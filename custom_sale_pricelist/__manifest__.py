# -*- coding: utf-8 -*-

{
    'name': "Customize: Sales and Pricelists",
    'summary': """
        Customize of Sales Module (Odoo Module: sale)
        Customize of Pricelists Module (Odoo Module: product)
    """,
    'description': """
        Customize of Sales Module (Odoo Core Module)
        Customize of Pricelists Module (Odoo Core Module)
        For set compare pricelist to keep price difference data on SO.
    """,
    'author': "Around Enterprise Consulting Co., Ltd.",
    'website': "https://www.around.co.th",
    'category': 'Sales',
    "version": "15.0.1.0.0",
    'depends': ['sale_management', 'hr', 'product', 'custom_sale'],
    # always loaded
    'data': [
        'data/email_template_not_approve.xml',
        'views/product_pricelist_view.xml',
        'views/sale_order_view.xml',
    ],
}
