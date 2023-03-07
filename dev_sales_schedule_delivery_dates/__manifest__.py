# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################

{
    'name': 'Schedule Delivery Dates, Sale Delivery Dates',
    'version': '1.0',
    'sequence': 1,
    'category': 'Generic Modules/Tools',
    'description':
        """
        This Module add below functionality into odoo

        Schedule Delivery Date\n
        
  delivery by dates , sale delivery , sale delivery dates, sale based on delivery date, sale different delivery, delivery date
Sale Delivery by Dates
create different delivery order for sale order based on given delivery date on sale order line
Delivery Date Scheduler for website
Sales delivery date odoo
How can we schedule sales delivery by dates
How can we schedule sales delivery by dates in odoo
Sale Delivery Schedule
Sale delivery date
Sales delivery by dates 
Sale delivery by dates with odoo app
Sales delivery odoo apps
Sale delivery schedule odoo app
Sale delivery schedule odoo
Odoo Sale Delivery by Dates
Odoo create different delivery order for sale order based on given delivery date on sale order line
Odoo Delivery Date Scheduler for website
Manage Sales Delivery date 
Odoo How can we schedule sales delivery by dates
Odoo Sale Delivery Schedule
Odoo Sale delivery date
Odoo Sales delivery by dates 
Different delivery order for sale order
Odoo Different delivery order for sale order
Easy to use with no configuration
Odoo Easy to use with no configuration
Delivery order manage 
Odoo Delivery Order manage 
Confirm the sale Order 
Odoo Confirm the sale Order 
View delivery order 
Odoo view delivery order 
Delivery order management 
Odoo Delivery order management       

    """,
    'summary': 'odoo app will schedule different delivery orders for sale order based on given delivery dates on sale order line, sale delivery by date,Sale Delivery Schedule, sale based on delivery date, sale different delivery,delivery by dates',
    'depends': ['sale_management','stock'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/schedule_delivery_view.xml',
        'views/sale.xml',
        ],
    'demo': [],
    'test': [],
    'css': [],
    'qweb': [],
    'js': [],
    'images': ['images/main_screenshot.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    
    #author and support Details
    'author': 'DevIntelle Consulting Service Pvt.Ltd',
    'website': 'http://www.devintellecs.com',    
    'maintainer': 'DevIntelle Consulting Service Pvt.Ltd', 
    'support': 'devintelle@gmail.com',
    'price':22.0,
    'currency':'EUR',
    'live_test_url':'https://youtu.be/vfv_JWaEltM',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
