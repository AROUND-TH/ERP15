from odoo import models, fields, _


class PurchaseReport(models.Model):
    _inherit = "purchase.report"

    lc_number = fields.Char(string="L/C Number")

    def _select(self):
        return super()._select() + ", po.lc_number as lc_number"

    def _group_by(self):
        return super()._group_by() + ", po.lc_number"
