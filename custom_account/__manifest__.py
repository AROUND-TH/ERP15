# -*- coding: utf-8 -*-

{
    'name': "Customize: Accounting",
    'summary': """
        Customize of Invoicing Module (Odoo Module: account)
        Customize of Accounting Module (Odoo Module: account_accountant)
    """,
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
    'category': 'Accounting',
    "version": "15.0.6.0.0",
    'depends': ['account', 'account_accountant', 'account_asset', 'custom_partner'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/account_bank_account_view.xml',
        'views/select_journal_config_view.xml',
        'views/account_payment_view.xml',
        'views/account_payment_register_view.xml',
        'views/account_asset_view.xml',
        'views/account_billing_customer_view.xml',
        'views/account_billing_vendor_view.xml',
        'views/receipt_billing_customer_view.xml',
        'views/pay_billing_vendor_view.xml',
        'views/account_account_views.xml',
        'views/account_move_views.xml',
        'views/account_report.xml',
        'wizards/select_invoice.xml',
        'reports/account_asset_transfer.xml',
        'reports/account_billing_customer.xml',
        'reports/account_billing_vendor.xml',
        'reports/receipt_billing_customer.xml',
        'reports/pay_billing_vendor.xml',
        'reports/report_payment_receipt_templates.xml',
        'reports/report_invoice_credit_notes.xml',
        'reports/report_invoice_with_payments.xml',
        'reports/report_receipt_bill.xml',
        'reports/general_journal_report.xml',
        'reports/report_invoice_with_payments_layout.xml',
    ],
    'assets': {
        'web.report_assets_common': [
            'custom_account/static/src/scss/report_assets_common.scss',
        ],
    }
}
