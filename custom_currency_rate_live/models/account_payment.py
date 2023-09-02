# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning, UserError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    currency_rate = fields.Float(compute='_compute_currency_rate', string='Rates')

    @api.depends("date")
    def _compute_currency_rate(self):
        for rec in self:
            if rec.currency_id.name == 'THB':
                rec.currency_rate = 1.00
            
            else:
                currency_rate_id =  self.env['res.currency.rate'].search([
                    ('name', '<=', rec.date),
                    ('currency_id', '=', rec.currency_id.id)
                ], limit=1)
                rec.currency_rate = 1.00/currency_rate_id.rate