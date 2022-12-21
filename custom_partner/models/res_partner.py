from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_customer = fields.Boolean('Is a Customer')
    is_vendor = fields.Boolean('Is a Vendor')

