from odoo import api, models, fields
from .group_purchase import FilterGroupPurchase


class AccountMove(models.Model, FilterGroupPurchase):
    _inherit = "account.move"

    def get_domain_partner(self):
        domain = [('type', '!=', 'private'), ('company_id', 'in', (False, self.env.user.company_id.id))]
        if self._context.get('filter_group_purchase'):
            domain = self._get_domain_filter_group_purchase(domain, 'vendor_group_id')
        return domain

    vendor_group_id = fields.Many2one(related="partner_id.vendor_group_id")
    partner_id = fields.Many2one('res.partner', domain=get_domain_partner)

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        if self._context.get('filter_group_purchase'):
            args = self._get_domain_filter_group_purchase(args, 'partner_id.vendor_group_id')
        return super().name_search(name, args, operator, limit)

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

    def name_get(self):
        result = []
        for rec in self:
            name = '%s - %s' % (rec.name, rec.vendor_group_id.name)
            result.append((rec.id, name))
        return result
