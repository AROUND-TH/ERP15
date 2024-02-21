# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Custom Live Currency Exchange Rate',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'description': """Import exchange rates from the Internet.
""",
    'depends': [
        'account',
        'currency_rate_live',
    ],
    'data': [
        'data/ir_scheduler_data.xml',
        'views/res_config_settings_views.xml',
        'views/account_move_views.xml',
        'views/account_payment_view.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}
