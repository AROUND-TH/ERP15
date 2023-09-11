from odoo import api, models


class Partner(models.Model):
    _inherit = "res.partner"

    def _get_domain_filter_group_purchase(self, domain):
        ir_config = self.env['ir.config_parameter'].sudo()
        vendor_group_id = ir_config.get_param('car_order_vendor_group_car')
        purchase_general = self.env.user.has_group('car_order.purchase_general')
        purchase_car = self.env.user.has_group('car_order.purchase_car')
        if purchase_general != purchase_car:
            _domain = ['vendor_group_id', '=', int(vendor_group_id)] if purchase_car else [
                'vendor_group_id', '!=', int(vendor_group_id)]
            domain.insert(0, _domain)
        return domain

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        if self._context.get('filter_group_purchase'):
            args = self._get_domain_filter_group_purchase(args)
        if self._context.get('filter_group_sale_salesman'):
            crm_team_id = self.env.user.crm_team_id
            if self.env.user.group_sale_salesman() and crm_team_id:
                args.insert(0, ['team_id', '=', crm_team_id.id])
        return super().name_search(name, args, operator, limit)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, **read_kwargs):
        if self._context.get('filter_group_purchase'):
            args = self._get_domain_filter_group_purchase(domain)
        if self._context.get('filter_group_sale_salesman'):
            crm_team_id = self.env.user.crm_team_id
            if self.env.user.group_sale_salesman() and crm_team_id:
                domain.insert(0, ['team_id', '=', crm_team_id.id])
        return super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if self._context.get('filter_group_purchase'):
            domain = self._get_domain_filter_group_purchase(domain)
        if self._context.get('filter_group_sale_salesman'):
            crm_team_id = self.env.user.crm_team_id
            if self.env.user.group_sale_salesman() and crm_team_id:
                domain.insert(0, ['team_id', '=', crm_team_id.id])
        return super().read_group(domain, fields, groupby, offset, limit, orderby, lazy)
