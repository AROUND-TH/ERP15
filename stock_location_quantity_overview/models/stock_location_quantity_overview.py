# -*- coding: utf-8 -*-


from odoo import api, fields, models, _


class StockLocationQuantity(models.TransientModel):
    _name = 'stock.location.quantity.overview'
    _description = 'Stock Location Quantity Overview'


    location_id = fields.Many2one("stock.location", string="Location", required=True)
    company_id = fields.Many2one("res.company", "Company", required=True, readonly=True, default=lambda self: self.env.company)
    hierarchy = fields.Boolean('Location hierarchy')


    def stock_location_overview(self):
        self.ensure_one()
        location_id = self.location_id.id
        self.env['stock.quant']._merge_quants()
        self.env['stock.quant']._unlink_zero_quants()
        domain = [('location_id', '=', location_id)]
        if self.hierarchy:
            domain = [('location_id', 'child_of', location_id)]
        return {
            'domain': domain,
            'name': _("Stock Location Quantity Overview"),
            'res_model': 'stock.quant',
            'views': [(self.env.ref('stock_location_quantity_overview.view_stock_location_quantity_overview_tree').id, "tree"),(self.env.ref('stock.view_stock_quant_pivot').id, "pivot")],
            'context' : {'search_default_productgroup': 1},
            'type': 'ir.actions.act_window',
            }
