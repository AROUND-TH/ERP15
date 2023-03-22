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
        'fleet_product_link',
    ],
    "data": [
        "report/car_order_report.xml",
        "report/car_order_template.xml",
        "data/ir_sequence_data.xml",
        "security/ir.model.access.csv",
        "views/car_order.xml",
    ]
}
