# -*- coding: utf-8 -*-

{
    'name': "Customize: Purchase",
    'summary': """
        Customize of Purchase Module
    """,
    'description': """
        Customize of Purchase Module
    """,
    'author': "Around Enterprise Consulting Co., Ltd.",
    'website': "https://www.around.co.th",
    'category': 'Purchase',
    "version": "15.0.1.0.0",
    'depends': ['product', 'hr', 'purchase', 'purchase_stock'],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/po_approval_security.xml',
        'data/email_purchase_order_request.xml',
        'data/email_purchase_order_approved.xml',
        'data/ir_config_parameter_data.xml',
        'settings/purchase_config_settings_view.xml',
        'wizard/purchase_receive_service.xml',
        'views/purchase_view.xml',
        'views/release_procedure_view.xml',
        'views/authentication_view.xml',
        'report/purchase_reports.xml',
        'report/purchase_order_templates.xml',
    ],
}
