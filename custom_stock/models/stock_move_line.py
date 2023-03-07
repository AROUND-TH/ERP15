from odoo import models, fields


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    sale_id = fields.Many2one(related="picking_id.sale_id", string="Order No.")
