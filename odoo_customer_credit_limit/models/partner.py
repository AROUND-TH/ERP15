# -*- coding: utf-8 -*-

from odoo import _, models, fields, api
import logging
_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    
    @api.onchange('credit_rule_id')
    def _onchange_credit_rule_id(self):
        self.credit_limit = self.credit_rule_id.credit_limit
    
    credit_rule_id = fields.Many2one(
        'partner.credit.rule',
        string='Credit Limit Rule',
        domain="[('partner_id', '=', id)]"
    ) #edit

    is_credit_manager = fields.Boolean(
        string='Credit Manager',
        compute='_compute_credit_manager'
    )

    internal_code = fields.Char(
        string='Internal Code',
    ) #edit

    credit_days = fields.Integer(compute='_compute_credit_days', string='Days') #edit
    code_for_credit = fields.Char(compute='_compute_code_for_credit', string='Code For Credit') #edit

    def action_create_credit_rule(self):

        return {
            'name': _('Create Create Rule'),
            'view_mode': 'form',
            'res_model': 'wizard.credit.rule',
            'view_id': self.env.ref('odoo_customer_credit_limit.create_credit_rule_view_form').id,
            'type': 'ir.actions.act_window',
            'context': {
                'default_partner_id': self.id,
                'default_code': self.code_for_credit,
                'default_credit_days': self.credit_days,
                'default_credit_limit': self.credit_limit,
                'default_payment_term_id': self.property_payment_term_id.id,
            },
            'target': 'new'
        }
    
    def action_update_credit_rule(self):

        return {
            'name': _('Update Create Rule'),
            'view_mode': 'form',
            'res_model': 'wizard.credit.rule',
            'view_id': self.env.ref('odoo_customer_credit_limit.update_credit_rule_view_form').id,
            'type': 'ir.actions.act_window',
            'context': {
                'default_partner_id': self.id,
                'default_name': self.credit_rule_id.name,
                'default_credit_type': self.credit_rule_id.credit_type,
                'default_credit_rule_id': self.credit_rule_id.id,
                'default_payment_term_id': self.property_payment_term_id.id,
                'default_code': self.code_for_credit,
                'default_credit_days': self.credit_days,
                'default_credit_limit': self.credit_limit,
            },
            'target': 'new'
        }
    
    def _compute_credit_manager(self):
        for line in self:
            if self.user_has_groups('odoo_customer_credit_limit.group_sale_credit_control'):
                line.is_credit_manager = True
            else:
                line.is_credit_manager = False

    def _compute_code_for_credit(self): #edit
        for line in self:
            code = line.internal_code + '-' + line.name if line.internal_code else line.name
            line.code_for_credit = code

    @api.depends('property_payment_term_id')
    def _compute_credit_days(self): #edit
        for line in self:
            days = sum(term_line.days for term_line in line.property_payment_term_id.line_ids)
            # for term_line in line.property_payment_term_id.line_ids:
            #     if term_line.option == 'day_after_invoice_date':
            line.credit_days = days
