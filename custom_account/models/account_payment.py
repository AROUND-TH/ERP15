# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning, UserError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    bank_account_id = fields.Many2one(
        'account.bank.account',
        string='Bank Account',
        required=False,
        readonly=False,
        states={'posted': [('readonly', True)]},
        copy=False,
    )

    check_detail = fields.Char('Check Detail')
    reconcile_status = fields.Char(string='Reconcile', compute='_compute_reconcile_state')
    reconcile_state = fields.Selection(
        selection=[
            ('not_reconcile', 'Not Reconcile'),
            ('reconciled', 'Reconciled'),
        ], 
        string='Reconcile Status', 
        compute='_compute_reconcile_state', 
        store=False,
        readonly=True,
        default='not_reconcile',
    )
    note = fields.Text(string='Notes')


    @api.depends('state', 'is_reconciled', 'reconciled_invoices_count', 'reconciled_bills_count', 'reconciled_statements_count')
    def _compute_reconcile_state(self):
        for rec in self:

            if rec.state == 'posted':
                invoices_type = ''
                len_invoice = 0

                if rec.reconciled_invoices_type == 'invoice':
                    invoices_type = 'Invoice' if rec.payment_type == 'inbound' else 'Bill'
                    len_invoice = len(rec.reconciled_invoice_ids) if rec.payment_type == 'inbound' else len(rec.reconciled_bill_ids)
                else:
                    invoices_type = 'Credit Note'
                    len_invoice = len(rec.reconciled_invoice_ids)

                if rec.is_reconciled:
                    rec.reconcile_state = 'reconciled'
                else:
                    count = rec.reconciled_invoices_count + rec.reconciled_bills_count + rec.reconciled_statements_count
                    if count > 0:
                        rec.reconcile_state = 'reconciled'
                    else:
                        rec.reconcile_state = 'not_reconcile'

                if len_invoice > 0:
                    rec.reconcile_status = '%s %s' %(len_invoice, invoices_type)
                elif rec.is_reconciled:
                    rec.reconcile_status = 'Reconciled'
                else:
                    rec.reconcile_status = 'Payment Matching'

            else:   
                rec.reconcile_state = 'not_reconcile'
                rec.reconcile_status = 'Draft' if rec.state == 'draft' else 'Cancelled'


    # @Override method _get_valid_liquidity_accounts
    def _get_valid_liquidity_accounts(self):
        return (
            self.bank_account_id.account_code,
            self.journal_id.default_account_id,
            self.payment_method_line_id.payment_account_id,
            self.journal_id.company_id.account_journal_payment_debit_account_id,
            self.journal_id.company_id.account_journal_payment_credit_account_id,
            self.journal_id.inbound_payment_method_line_ids.payment_account_id,
            self.journal_id.outbound_payment_method_line_ids.payment_account_id,
        )


    # @Override method create
    @api.model_create_multi
    def create(self, vals_list):
        payments = super(AccountPayment, self).create(vals_list)

        # @Add check bank_account_id field for addition logic.
        for payment in payments:
            # if payment.payment_type == 'inbound':
            #     if (payment.bank_account_id) and (payment.journal_id.type == 'bank'):

            if payment.bank_account_id:
                if not payment.bank_account_id.account_code:
                    raise UserError(_('Please check "Account Code" of selected Bank Account !!'))

                lines = payment.move_id.line_ids
                if lines:
                    lines[0].account_id = payment.bank_account_id.account_code

        return payments


    # @Override method write
    def write(self, vals):
        res = super(AccountPayment, self).write(vals)

        # @Add check bank_account_id field for addition logic.
        for rec in self:
            if not rec.state == 'posted':
                # if rec.payment_type == 'inbound':
                #     if (rec.bank_account_id) and (rec.journal_id.type == 'bank'):

                if rec.bank_account_id:
                    if not rec.bank_account_id.account_code:
                        raise UserError(_('Please check "Account Code" of selected Bank Account !!'))

                    lines = rec.move_id.line_ids
                    if lines:
                        # lines[0].account_id = rec.bank_account_id.account_code
                        lines[0].update({'account_id': rec.bank_account_id.account_code})

        return res


    # -------------------------------------------------------------------------
    # SYNCHRONIZATION account.payment <-> account.move
    # -------------------------------------------------------------------------

    # @Override method _synchronize_from_moves
    def _synchronize_from_moves(self, changed_fields):
        ''' Update the account.payment regarding its related account.move.
        Also, check both models are still consistent.
        :param changed_fields: A set containing all modified fields on account.move.
        '''
        if self._context.get('skip_account_move_synchronization'):
            return

        for pay in self.with_context(skip_account_move_synchronization=True):

            # After the migration to 14.0, the journal entry could be shared between the account.payment and the
            # account.bank.statement.line. In that case, the synchronization will only be made with the statement line.
            if pay.move_id.statement_line_id:
                continue

            move = pay.move_id
            move_vals_to_write = {}
            payment_vals_to_write = {}

            if 'journal_id' in changed_fields:
                if pay.journal_id.type not in ('bank', 'cash'):
                    raise UserError(_("A payment must always belongs to a bank or cash journal."))

            if 'line_ids' in changed_fields:
                all_lines = move.line_ids

                # @Remark to skip this check.
                # liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

                # if len(liquidity_lines) != 1:
                #     raise UserError(_(
                #         "Journal Entry %s is not valid. In order to proceed, the journal items must "
                #         "include one and only one outstanding payments/receipts account.",
                #         move.display_name,
                #     ))

                # if len(counterpart_lines) != 1:
                #     raise UserError(_(
                #         "Journal Entry %s is not valid. In order to proceed, the journal items must "
                #         "include one and only one receivable/payable account (with an exception of "
                #         "internal transfers).",
                #         move.display_name,
                #     ))

                # if writeoff_lines and len(writeoff_lines.account_id) != 1:
                #     raise UserError(_(
                #         "Journal Entry %s is not valid. In order to proceed, "
                #         "all optional journal items must share the same account.",
                #         move.display_name,
                #     ))

                if any(line.currency_id != all_lines[0].currency_id for line in all_lines):
                    raise UserError(_(
                        "Journal Entry %s is not valid. In order to proceed, the journal items must "
                        "share the same currency.",
                        move.display_name,
                    ))

                if any(line.partner_id != all_lines[0].partner_id for line in all_lines):
                    raise UserError(_(
                        "Journal Entry %s is not valid. In order to proceed, the journal items must "
                        "share the same partner.",
                        move.display_name,
                    ))

            # @Remark to skip this check.
            #     if counterpart_lines.account_id.user_type_id.type == 'receivable':
            #         partner_type = 'customer'
            #     else:
            #         partner_type = 'supplier'

            #     liquidity_amount = liquidity_lines.amount_currency

            #     move_vals_to_write.update({
            #         'currency_id': liquidity_lines.currency_id.id,
            #         'partner_id': liquidity_lines.partner_id.id,
            #     })
            #     payment_vals_to_write.update({
            #         'amount': abs(liquidity_amount),
            #         'partner_type': partner_type,
            #         'currency_id': liquidity_lines.currency_id.id,
            #         'destination_account_id': counterpart_lines.account_id.id,
            #         'partner_id': liquidity_lines.partner_id.id,
            #     })
            #     if liquidity_amount > 0.0:
            #         payment_vals_to_write.update({'payment_type': 'inbound'})
            #     elif liquidity_amount < 0.0:
            #         payment_vals_to_write.update({'payment_type': 'outbound'})

            # move.write(move._cleanup_write_orm_values(move, move_vals_to_write))
            # pay.write(move._cleanup_write_orm_values(pay, payment_vals_to_write))

