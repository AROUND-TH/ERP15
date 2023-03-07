# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt Ltd. See LICENSE file for full copyright and licensing details.

{
    'name': ' Customer Credit Limit on Sales',
    'version': '3.1.33',
    'category' : 'Sales/Sales',
    'license': 'Other proprietary',
    'price': 99.0,
    'currency': 'EUR',
    'summary': """Allow you to set credit limit on customer and raise warning if customer reached limits.""",
    'description': """
This module allows user Can Not confirm quotation since customer has reached credit limit
In this module it will set Credit Lmit Rule for the customer
Allowed customer to select Credit limit rule
Creditlimit set by the Credit Limit Rule
Credit Limit Rule will be Worked Two Way
1.Receivable Amount of Customer
Credit Limit Warning During Sales Order Confirmation
Credit Limit Rule
customer credit
customer limit
limit credit
credit limit
credit limit sale
Credit Limit Rules
advance credit limit
2.Due Amount Till Days
Customer on Credit Limit Hold
customers_credit_limit
Partner Credit Limit
partner_credit_limit
Customer Credit Limit Warning On Confirm Sales Order
Customer Credit Warning on Sales
dev_customer_credit_limit
Exceeded Credit Limit
Configure Customer Credit Limit
Due Amount Till Days will Calculate Customer's Receivable amount from Unpaid Invoice and also from Selling Products Amount
Due Amount Till Days Credit limit rule will consider Selling Products if in Credit Limit Rule Categories and /or Product Template
Due Amount Till Days Credit limit rule and Products it will checked Selling products in Template and/or categories or not and count selling product amount and Unpaid Invoice Amount
Change Customer Credit Limit
Odoo Credit Limit Advance
Email: contact@probuse.com
odoo credit limit
odoo customer credit limit
odoo sales order credit limit
credit limit customer odoo
customer credit limit in odoo
credit limit rules
credit limit on customer odoo
Menus:
Configuration/Due Amount Till Days
credit limit
customer_credit_limit
    """,
    'author': 'Probuse Consulting Service Pvt. Ltd.',
    'website': 'http://www.probuse.com',
    'support': 'contact@probuse.com',
    'images': ['static/description/img.jpg'],
    # 'live_test_url': 'https://youtu.be/X4pSQR_YwXc',
    'live_test_url': 'http://probuseappdemo.com/probuse_apps/odoo_customer_credit_limit/135',#'https://youtu.be/e5HmSqqPRJU',
    'depends': [
            'sale',
            'account',
            'sales_team',
    ],
    'data':[
        'security/ir.model.access.csv',
        'security/sales_team_security.xml',
        'views/res_partner_views.xml',
        'views/sale_order_view.xml',
        'views/partner_credit_rule_view.xml',
        'views/credit_message_error_view.xml',
        'wizard/wizard_credit_rule_view.xml',
    ],
    'installable' : True,
    'application' : False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
