from odoo import api, models


class Lead(models.Model):
    _inherit = "crm.lead"

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, **read_kwargs):
        if self._context.get('filter_group_sale_salesman'):
            crm_team_id = self.env.user.crm_team_id
            if self.env.user.group_sale_salesman() and crm_team_id:
                domain.insert(0, ['team_id', '=', crm_team_id.id])
        return super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if self._context.get('filter_group_sale_salesman'):
            crm_team_id = self.env.user.crm_team_id
            if self.env.user.group_sale_salesman() and crm_team_id:
                domain.insert(0, ['team_id', '=', crm_team_id.id])
        return super().read_group(domain, fields, groupby, offset, limit, orderby, lazy)
