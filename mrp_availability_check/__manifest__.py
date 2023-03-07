# -*- coding: utf-8 -*-
# Copyright (c) Open Value All Rights Reserved

{
    'name': 'MRP Availability Check',
    'summary': 'MRP Availability Check',
    'version': "15.0.1.0",
    'category': 'Manufacturing',
    'website': 'www.openvalue.cloud',
    'author': 'OpenValue',
    'support': 'info@openvalue.cloud',
    'license': 'Other proprietary',
    'price': 800.00,
    'currency': 'EUR',
    'depends': [
        'mrp',
        'mrp_subcontracting',
        'purchase_stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        #'views/mrp_bom_views.xml',
        'reports/report_mrp_bom_explosion.xml',
        'reports/report_mrp_availability_check.xml',
        'wizard/mrp_availability_check_views.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    'images': ['static/description/banner.png'],
}