# -*- coding: utf-8 -*-

{
    'name': "Report Vehicle in Pipeline 2",
    'summary': """
        Report Vehicle in Pipeline 2
    """,
    'description': """
        Report Vehicle in Pipeline 2
    """,
    'author': "Around Enterprise Consulting Co., Ltd.",
    'website': "https://www.around.co.th",
    'category': 'Inventory',
    "version": "15.0.1.0.0",
    'depends': ['stock', 'purchase'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/report_vehicle_pipeline_views.xml',
    ],
}
