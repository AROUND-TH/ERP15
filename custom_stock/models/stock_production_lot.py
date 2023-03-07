from odoo import fields, models


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    ref = fields.Char(string="Internal Reference (BIN)")
    batch = fields.Char(string="Batch")
    product_grade = fields.Selection([('a', 'A'), ('b', 'B'), ('c', 'C')], string="Product Grade")
    remark = fields.Char(string="remark")
    product_qty = fields.Float(store=True)
