# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sale_discount_account_id = fields.Many2one('account.account', string="Sale Discount Account", config_parameter="sale_discount_account_id")
