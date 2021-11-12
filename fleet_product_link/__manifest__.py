# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt Ltd. See LICENSE file for full copyright and licensing details.

{
    'name': 'Product Integration with Fleet Vehicle',
    'version': '5.1.4',
    'currency': 'EUR',
    'price': 9.0,
    'license': 'Other proprietary',
    'category': 'Human Resources/Fleet',
    'summary': 'This app allow you to create product from vehicle fleet.',
    'description': """
fleet
vehicle
product
Product Integration with Fleet Vehicle
fleet product
This app allow you to create product from vehicle fleet
product fleet
vehicle product
product vehicle

""",
    'author': 'Probuse Consulting Service Pvt. Ltd.',
    'website': 'www.probuse.com',
    'depends': ['fleet','product','sale','sale_stock'],
    'support': 'contact@probuse.com',
    'live_test_url': 'https://probuseappdemo.com/probuse_apps/fleet_product_link/721',#'https://youtu.be/MnF5wpx8WMU',
    'images': ['static/description/image.png'],
    'data': [
            'security/ir.model.access.csv',
            'wizard/create_product_view.xml',
            'views/fleet_product_inherited.xml',
            'views/product_templete_inherited.xml',
            'views/product_product_inherited.xml',
         ],
    'installable': True,
    'application': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

