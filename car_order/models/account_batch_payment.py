from odoo import api, models, fields
from .group_purchase import FilterGroupPurchase


class AccountBatchPayment(models.Model, FilterGroupPurchase):
    _inherit = "account.batch.payment"

    vendor_group_id = fields.Many2one("vendor.group", compute="_compute_vendor_group", store=True)

    @api.depends("payment_ids", "payment_ids.partner_id")
    def _compute_vendor_group(self):
        ir_config = self.env['ir.config_parameter'].sudo()
        vendor_group_car_id = ir_config.get_param('car_order_vendor_group_car')
        for rec in self:
            vendor_group_id = False
            groups = rec.payment_ids.mapped('vendor_group_id')
            if len(groups) == 1 and groups.id == int(vendor_group_car_id):
                vendor_group_id = groups
            rec.vendor_group_id = vendor_group_id

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, **read_kwargs):
        if self._context.get('filter_group_purchase'):
            domain = self._get_domain_filter_group_purchase(domain, 'vendor_group_id')
        return super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if self._context.get('filter_group_purchase'):
            domain = self._get_domain_filter_group_purchase(domain, 'vendor_group_id')
        return super().read_group(domain, fields, groupby, offset, limit, orderby, lazy)
