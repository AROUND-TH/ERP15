{
    'name': "Car Order",
    'summary': """
        Car OrderModule 
    """,
    'description': """""",
    'author': "Around Enterprise Consulting Co., Ltd.",
    'website': "https://www.around.co.th",
    "version": "15.0.0.8.0",
    "depends": [
        'base',
        'product',
        'account',
        'sale',
        'hr',
        'fleet_product_link',
    ],
    "data": [
        "data/ir_sequence_data.xml",
        "data/paper_format.xml",
        "report/car_order_report.xml",
        "report/car_order_template.xml",
        "report/quotation_template.xml",
        "security/ir.model.access.csv",
        "views/res_config_settings_view.xml",
        "views/product_template.xml",
        "views/car_order.xml",
    ]
}
