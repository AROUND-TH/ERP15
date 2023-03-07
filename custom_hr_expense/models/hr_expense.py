# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import string
from odoo.exceptions import UserError
from odoo.tools import email_split, float_is_zero, float_repr
from odoo import api, fields, Command, models, _
from odoo.tools.misc import clean_context, format_date

class HrExpense(models.Model):
    _inherit = "hr.expense"

    def _prepare_move_values(self):
        super(HrExpense, self)._prepare_move_values()
        """
        This function prepares move values related to an expense
        """
        self.ensure_one()
        print()
        journal = self.sheet_id.bank_journal_id if self.payment_mode == 'company_account' else self.sheet_id.journal_id
        account_date = self.sheet_id.accounting_date or self.date
        move_values = {
            'journal_id': journal.id,
            'company_id': self.sheet_id.company_id.id,
            'date': account_date,
            'ref': self.sheet_id.document_number,
            # force the name to the default value, to avoid an eventual 'default_name' in the context
            # to set it to '' which cause no number to be given to the account.move when posted.
            'name': '/',
        }
        return move_values
    
class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    document_number = fields.Char(string='Document No.',
        default='New',
        required=True,
        store=True, 
        index=True, 
        readonly=True, 
        copy=False)

    name_form = fields.Selection([
        ('adv_bill', 'ใบเบิกเงินทดรองจ่าย'),
        ('adv_clear', 'ใบเคลียร์เงินทดรองจาย'),
        ('exp_bill', 'ใบเบิกค่าใช้จ่าย'),
        ('ptt_bill', 'ใบเบิกเงินสดย่อย'),
    ], string='Name', required=True)


    def action_register_payment(self):
        ''' Open the account.payment.register wizard to pay the selected journal entries.
        :return: An action opening the account.payment.register wizard.
        '''
        return {
            'name': _('Register Payment'),
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'context': {
                'active_model': 'account.move',
                'active_ids': self.account_move_id.ids,
                'default_partner_bank_id': self.employee_id.sudo().bank_account_id.id,
                'default_communication': self.document_number,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }


    @api.model
    def create(self, values):
        if not values.get('document_number') or values.get('document_number') == 'New':
            document_number = self.env['ir.sequence'].next_by_code('hr.expense.sheet')
            values.update({
                'document_number': document_number
            })

        return super(HrExpenseSheet, self).create(values)
        