from odoo import api, fields, models


class StorageCategory(models.Model):
    _inherit = 'stock.storage.category'

    capacity_type = fields.Selection([('kg', 'kg'), ('pallet', 'Pallet')], default='kg', string="Unit", required=True)
    max_pallet = fields.Integer(string="Max Pallet")
    used = fields.Float('Used', digits='Product Unit of Measure', compute='_compute_used', store=True)
    used_percent = fields.Integer('Used(%)', compute='_compute_used', store=True)

    @api.onchange('capacity_type')
    def _onchange_capacity_type(self):
        if self.capacity_type == "pallet":
            self.max_weight = 0
        elif self.capacity_type == "kg":
            self.max_pallet = 0

    @api.depends('capacity_type', 'max_weight', 'max_pallet', 'location_ids.quant_ids.quantity')
    def _compute_used(self):
        for rec in self:
            used, used_percent = 0, 0
            if rec.capacity_type == "kg" and rec.max_weight:
                used = sum(rec.mapped('location_ids').mapped('quant_ids').mapped('product_gross_weight')) or 0
                used_percent = (100.0 * used) / rec.max_weight
            rec.used = used
            rec.used_percent = used_percent
