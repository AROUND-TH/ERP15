# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Export Product Stock in Excel and PDF Reports',
    'version': '14.0.0.3',
    'category': 'Extra Tools',
    'sequence': 14,
    'summary': 'Export Stock Information In Excel export stock in excel export stock in xls export stock data in excel export product stock in xls   product stock data export stock valuation export product stock valuation export product stock details product stock data',
    'price': 29,
    'currency': "EUR",

    'description': """
    Export product stock in excel export stock data export stock information
    export product report in pdf
    export stock data in excel report
    export product stock data in excel report
    export stock data in pdf report
    export product stock data in pdf report
    stock export report data
    product stock data export from Odoo
    product data export from Odoo
    stock valuation export product stock valuation export
    stock in-out export in odoo product stock excel export
    product excel export product stock pdf reports
    export product variants details in pdf
    export product details in pdf
    export product variants details in excel
    export product details in excel
    Export Stock Information Reports
    Export Stock Information excel Reports
    Export Stock Information pdf Reports

    export product stock details in pdf
    export product stock details in pdf
    export product stock variants details in excel
    export product stock details in excel

    export stock details in pdf
    export stock valuation details in pdf for products
    export stock variants details in excel
    export stock details in excel
    This Odoo apps helps to export current stock information for all products in one or several warehouses in single spreadsheet
     and pdf report, it also highlights the stock quantity in the report according to its availability.
     This Odoo apps provide filter of warehouse , product categories ,date range (Start date and end date) filter, 
     Supplier/vendors filter in wizard to generate the product current stock valuation reports in pdf and Excel format.
""",
    'license':'OPL-1',
    'author': 'BrowseInfo',
    'website': 'https://www.browseinfo.in',
    'images': [],
    'depends': ['base','sale','stock','purchase'],
    'data': [
        'security/ir.model.access.csv',
        'report/export_stock_info_templates.xml',
        'report/report.xml',
        'wizard/export_stock_info_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    "live_test_url": "https://youtu.be/MIvxKKnA5mU",
    "images":['static/description/Banner.png'],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
