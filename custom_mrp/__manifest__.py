# -*- coding: utf-8 -*-

{
    'name': "Customize: Manufacturing",
    'summary': """
        Customize of Manufacturing Module (Odoo Module: mrp)
    """,
    'description': """
        Customize of Manufacturing Module (Odoo Core Module)
        For set and display of "Product Name of Component" for Manufacturing.
    """,
    'author': "Around Enterprise Consulting Co., Ltd.",
    'website': "https://www.around.co.th",
    'category': 'Manufacturing',
    "version": "14.0.1.0.0",
    'depends': ['mrp','custom_product','mrp_shop_floor_control'],
    'data': [
        'security/ir.model.access.csv',
        'views/mrp_bom_view.xml',
        'views/mrp_production_view.xml',
        'views/res_config_settings.xml',
        'wizard/wizard_consumption_stock_move_view.xml'
    ],
}
