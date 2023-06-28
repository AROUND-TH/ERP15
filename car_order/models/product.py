from odoo import models, fields


class Product(models.Model):
    _inherit = "product.template"

    is_car_order_expenses = fields.Boolean(default=True, string="ค่าใช้จ่ายสำหรับขายรถ")
