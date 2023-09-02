from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = "sale.order"

    car_order_id = fields.Many2one('car.order', readonly=True)
