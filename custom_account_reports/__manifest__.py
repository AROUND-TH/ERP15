# -*- coding: utf-8 -*-

{
    'name': "Customize: Accounting Reports",
    'summary': "View and create reports",
    'description': """
        Customize of Invoicing Module (Odoo Core Module)\n
        Customize of Accounting Module (Odoo Enterprise Core Module)\n
        For setting "Configuration > Banks > Bank Account" to set Bank Account data.\n
        For setup "Customers > Payments > Journal Entry" with Account Code of Bank Account.\n
        For customize "Accounting > Management > Asset" for asset management features.\n
        For new module "Customers > Billing Note" to do process of customers billing.\n
        For new module "Customers > Receipt Customer Bill" to do process of receipt customer bill.\n
        For new module "Vendors > Bill Acceptance" to do process of vendors billing.\n
        For new module "Vendors > Pay Vendor Bill" to do process of pay vendor bill.\n
    """,
    'author': "Around Enterprise Consulting Co., Ltd.",
    'website': "https://www.around.co.th",
    'category': 'Accounting/Accounting',
    "version": "15",
    'depends': ['account_3way_match', 'account_reports', 'stock_account'],
    'data': [
        'security/ir.model.access.csv',
        'data/account_report_data.xml',
        'views/setting_production_cost_view.xml',
        'views/setting_cost_of_sales_view.xml',
    ],
}
