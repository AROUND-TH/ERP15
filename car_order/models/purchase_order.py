from odoo import api, models, fields
from .group_purchase import FilterGroupPurchase


class PurchaseOrder(models.Model, FilterGroupPurchase):
    _inherit = "purchase.order"

    def get_domain_partner(self):
        ir_config = self.env['ir.config_parameter'].sudo()
        vendor_group_id = ir_config.get_param('car_order_vendor_group_car')
        domain = ['|', ('company_id', '=', False), ('company_id', '=', self.env.user.company_id.id)]
        if self._context.get('filter_vendor_group'):
            domain.append(('vendor_group_id', '=', int(vendor_group_id)))
        elif self._context.get('filter_group_purchase'):
            domain = self._get_domain_filter_group_purchase(domain, 'vendor_group_id')
        return domain

    partner_id = fields.Many2one('res.partner', domain=get_domain_partner)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, **read_kwargs):
        if self._context.get('filter_group_purchase'):
            domain = self._get_domain_filter_group_purchase(domain, 'partner_id.vendor_group_id')
        return super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if self._context.get('filter_group_purchase'):
            domain = self._get_domain_filter_group_purchase(domain, 'partner_id.vendor_group_id')
        return super().read_group(domain, fields, groupby, offset, limit, orderby, lazy)
