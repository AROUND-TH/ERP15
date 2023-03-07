{
    'name': "Customize: Sale",
    'summary': """
        Customize of Sale Module 
    """,
    'description': """""",
    'author': "Around Enterprise Consulting Co., Ltd.",
    'website': "https://www.around.co.th",
    "version": "15",
    "depends": [
        'base',
        'sale',
        'sale_stock',
        'custom_account',
        'hr',
        'sh_sale_quotation_order_number',
        'dev_sales_schedule_delivery_dates',
    ],
    "data": [
        "security/ir.model.access.csv",
        "report/sale_report.xml",
        "report/sale_report_templates.xml",
        "views/sale_order.xml",
        "views/authentication_view.xml",
    ]
}
