from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    crm_team_id = fields.Many2one('crm.team', string="Sales Team")

    def group_sale_salesman(self):
        return self.has_group('sales_team.group_sale_salesman') and not self.has_group(
            'sales_team.group_sale_salesman_all_leads')
