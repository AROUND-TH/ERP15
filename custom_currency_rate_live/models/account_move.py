# -*- coding: utf-8 -*-

import sys
from odoo import models, fields, api
import datetime
import re

class AccountMove(models.Model):
    _inherit = 'account.move'


    exchange_rate_date = fields.Date(compute='_compute_exchange_rate_date', string='Exchange Rate Date')
    payment_ref = fields.Char(compute='_compute_get_reference', string='Reference No. 1')
    invoice_ref = fields.Char(compute='_compute_get_reference', string='Reference No. 2')
    is_exchange_difference = fields.Boolean(compute='_compute_get_reference', string='Is Exchange Difference')
    currency_rate = fields.Float(compute='_compute_currency_rate', string='Rates')

    @api.depends("exchange_rate_date")
    def _compute_currency_rate(self):
        for rec in self:
            if rec.currency_id.name == 'THB':
                rec.currency_rate = 1.00
            
            else:
                currency_rate_id =  self.env['res.currency.rate'].search([
                    ('name', '<=', rec.exchange_rate_date),
                    ('currency_id', '=', rec.currency_id.id)
                ], limit=1)
                rec.currency_rate = 1.00/currency_rate_id.rate
            

    @api.depends("currency_id", "invoice_date", "date")
    def _compute_exchange_rate_date(self):
        for rec in self:
            if rec.currency_id and rec.invoice_date or rec.date:
                rate_date = rec.invoice_date if rec.invoice_date else rec.date 

                currency_rate_id =  self.env['res.currency.rate'].search([
                    ('name', '<=', rate_date),
                    ('currency_id', '=', rec.currency_id.id)
                ], limit=1)

                rec.exchange_rate_date = currency_rate_id.name
            else:
                rec.exchange_rate_date = False

    @api.depends("exchange_rate_date")
    def _compute_get_reference(self):
        for rec in self:

            journal_id = self.env['account.journal'].search([('name', '=', 'Exchange Difference')])
            payment_ref = ''
            invoice_ref = ''
            is_exchange_difference = False

            if journal_id and journal_id.id == rec.journal_id.id:

                is_exchange_difference = True
                line_ids = rec.line_ids._reconciled_lines()
                ref_id = False

                for line_id in line_ids:
                    if line_id not in rec.line_ids.ids:
                        move_line_id = self.env['account.move.line'].search([('id', '=', line_id)])
                        ref_id = move_line_id.move_id

                if ref_id:
                    payment_ref = ref_id.payment_id.name
                    invoice_ref = ref_id.ref

            rec.is_exchange_difference = is_exchange_difference
            rec.payment_ref = payment_ref
            rec.invoice_ref = invoice_ref
