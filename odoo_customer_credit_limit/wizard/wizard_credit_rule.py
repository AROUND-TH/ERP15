# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class WizardCreditRule(models.TransientModel):
    _name = 'wizard.credit.rule'
    _description = "Wizard Credit Rule"

    name = fields.Char(
        string='Name',
        required=True,
    )
    credit_rule_id = fields.Many2one(
        'partner.credit.rule',
        string='Credit Limit Rule'
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
    )
    payment_term_id = fields.Many2one(
        'account.payment.term',
        string='Payment Terms',
    )
    credit_limit = fields.Float('Credit Limits', required=True)
    credit_days = fields.Integer(string='Days', required=True)
    code = fields.Char(related='partner_id.code_for_credit', string='Code')
    credit_type = fields.Selection(
        selection=[
            ('days','Due Amount Till Days'),
        ],
        string='Credit Limit Formula',
        default='days',
        required=True
    )

    def action_create(self):
        credit_id = self.env['partner.credit.rule'].create({
            'name': self.name,
            'partner_id': self.partner_id.id,
            'credit_type': self.credit_type,
            'code': self.code,
            'credit_limit': self.credit_limit,
            'credit_days': self.credit_days,
        })

        return self.partner_id.update({ 'credit_rule_id': credit_id.id }) 

    def action_update(self):
    
        self.credit_rule_id.update({
            'code': self.code,
            'credit_type': self.credit_type,
            'credit_limit': self.credit_limit,
            'credit_days': self.credit_days,
        })
