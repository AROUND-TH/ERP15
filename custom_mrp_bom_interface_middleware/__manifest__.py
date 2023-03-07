{
    'name': "Customize: Manufacturing Bom Interface Middleware",
    'summary': """
        Customize of Manufacturing Order Module (Odoo Module: mrp)
    """,
    'description': """
        Customize of Manufacturing Order Module (Odoo Core Module)
        For set and display of "Product Name of Component" for Manufacturing.
    """,
    'author': "Around Enterprise Consulting Co., Ltd.",
    'website': "https://www.around.co.th",
    'category': 'Manufacturing',
    "version": "14.0.1.0.0",
    'depends': ['mrp', 'custom_product', 'product_expiry', 'custom_mrp', 'custom_success_message', 'excel_import_export_mrp'],
    'data': [
        "views/mrp_bom_view.xml"
    ],
}
