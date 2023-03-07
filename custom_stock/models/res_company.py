from odoo import models,fields 

class ResCompany(models.Model):
    _inherit = "res.company"

    company_name_en = fields.Char("Company Name En")