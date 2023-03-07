# -*- coding: utf-8 -*-

{
    'name': "Customize: Sales Quotation Report Template",
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
    'depends': ['sale_management','custom_sale','web_digital_sign','stock'],
    # always loaded
    'data': [
        'data/report_paper.xml',
        'reports/template.xml',
        'reports/quotation_report_template_th.xml',
        'reports/quotation_report_template_en.xml',
        'views/sale_order_view.xml',
        'reports/sale_report_quotation.xml',
        'reports/sale_report_delivery_order.xml',
    ],
    'assets': {
        'web.report_assets_common': [
            'custom_sale_quotation_report_template/static/src/less/report.less',
            ],
        },
}
