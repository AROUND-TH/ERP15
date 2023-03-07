from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class StockQuant(models.Model):
    _inherit = "stock.quant"

    product_categ_id = fields.Many2one(store=True)
    product_weight = fields.Float(related="product_id.weight")
    product_gross_weight = fields.Float(string="Gross Weight", compute="_compute_product_gross_weight", store=True)
    expiration_date = fields.Datetime(related="lot_id.expiration_date")
    alert_date = fields.Datetime(related="lot_id.alert_date")

    @api.depends("product_id", "quantity")
    def _compute_product_gross_weight(self):
        for rec in self:
            rec.product_gross_weight = rec.quantity * rec.product_id.weight

    @api.model
    def action_view_inventory(self):
        action = super().action_view_inventory()
        action['context'].update(search_default_locationgroup=1, search_default_product_category_group=1)
        return action

    @api.model
    def _update_available_quantity(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None,
                                   in_date=None):
        if location_id.storage_category_id:
            if location_id.max_weight < location_id.net_weight + (product_id.weight * quantity):
                raise ValidationError(_(f'{location_id.display_name} not enough weight for storage.'))
        return super()._update_available_quantity(product_id, location_id, quantity, lot_id, package_id, owner_id,
                                                  in_date)
