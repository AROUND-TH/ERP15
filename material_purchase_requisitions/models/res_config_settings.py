from odoo import fields, models


class StockConfigurationSettings(models.TransientModel):
    _inherit = "res.config.settings"

    requisitions_vendor = fields.Many2one('res.partner', string="Default Vendor", config_parameter="default_requisitions_vendor")
