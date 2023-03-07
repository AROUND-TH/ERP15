import json
from odoo import api, models, fields, _


class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    lot_id_domain = fields.Char(compute="_compute_lot_id_domain", readonly=True, store=False)
    location_id_domain = fields.Char(compute="_compute_location_id_domain", readonly=True, store=False)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        super()._onchange_product_id()
        self.lot_id = False
        self.location_id = False
        self.scrap_qty = 1

    @api.depends('lot_id')
    def _compute_location_id_domain(self):
        for rec in self:
            domain = json.dumps([('id', '=', 0)])
            if not rec.product_id or rec.state == "done":
                rec.location_id_domain = domain
                continue
            if rec.tracking == "lot":
                if rec.lot_id:
                    domain = json.dumps([
                        ('usage', '=', 'internal'),
                        ('company_id', 'in', [rec.company_id.id, False]),
                        ('id', 'in', rec.lot_id.quant_ids.mapped('location_id').ids)
                    ])
            else:
                quant_ids = self.env['stock.quant'].search([('product_id', '=', rec.product_id.id)])
                domain = json.dumps([
                        ('usage', '=', 'internal'),
                        ('company_id', 'in', [rec.company_id.id, False]),
                        ('id', 'in', quant_ids.mapped('location_id').ids)
                    ])
            rec.location_id_domain = domain

    @api.depends('product_id')
    def _compute_lot_id_domain(self):
        for rec in self:
            domain = json.dumps([('id', '=', False)])
            if rec.product_id and rec.state == "draft" and rec.tracking == "lot":
                domain = json.dumps([
                    ('product_id', '=', self.product_id.id),
                    ('company_id', '=', self.company_id.id),
                    ('product_qty', '>', 0)
                ])
                rec._compute_location_id_domain()
            rec.lot_id_domain = domain
