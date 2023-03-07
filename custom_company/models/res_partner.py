from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    company_details = fields.Html(translate=True)
