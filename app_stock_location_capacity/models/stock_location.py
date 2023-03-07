from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class StockLocation(models.Model):
    _inherit = "stock.location"

    capacity_type = fields.Selection(related="storage_category_id.capacity_type", string="Unit")
    max_weight = fields.Float('Max Weight', digits='Stock Weight')
    max_pallet = fields.Integer(string="Max Pallet")
    net_weight_percent = fields.Integer('Used(%)', compute='_compute_net_weight_percent', store=True)
    
    @api.constrains('max_weight', 'max_pallet')
    def _validate_max_weight(self):
        for rec in self:
            if rec.capacity_type == "pallet":
                continue
            storage_max_weight = rec.storage_category_id.max_weight
            using_weight = sum(
                self.search([('storage_category_id', '=', rec.storage_category_id.id), ('id', '!=', rec.id)]).mapped(
                    'max_weight'))
            space_can_use = storage_max_weight - using_weight
            if rec.max_weight > space_can_use:
                raise ValidationError(_(f'Capacity left available can be used {space_can_use} kg.'))

    @api.depends('storage_category_id', 'capacity_type', 'max_weight', 'net_weight')
    def _compute_net_weight_percent(self):
        for rec in self:
            percent = 0
            if rec.capacity_type == "kg":
                if rec.max_weight > 0:
                    percent = (100.0 * rec.net_weight) / rec.max_weight
                elif rec.net_weight:
                    percent = 100.0
            rec.net_weight_percent = percent

    def _check_can_be_used(self, product, quantity=0, package=None, location_qty=0):
        self.ensure_one()
        if self.storage_category_id:
            if self.max_weight < self.net_weight + product.weight * quantity:
                return False
        return super()._check_can_be_used(product, quantity, package, location_qty)


class StorageCategory(models.Model):
    _inherit = 'stock.storage.category'

    @api.constrains('max_weight')
    def _validate_max_weight(self):
        for rec in self:
            if rec.capacity_type == "pallet":
                continue
            using_weight = sum(rec.location_ids.mapped('max_weight'))
            if rec.max_weight < using_weight:
                raise ValidationError(_(f"Can't set Max Weight to be less than Using ( Using {using_weight} kg)"))

    def write(self, vals):
        result = super().write(vals)
        if vals.get('capacity_type'):
            if vals.get('capacity_type') == "pallet":
                self.location_ids.write({'max_weight': 0})
            else:
                self.location_ids.write({'max_pallet': 0})
        return result
