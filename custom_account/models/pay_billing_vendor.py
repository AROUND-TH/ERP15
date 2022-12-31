# -*- coding: utf-8 -*-

from lxml import etree

from odoo import models, fields, api, _
from odoo.exceptions import Warning, UserError, ValidationError

from collections import defaultdict

import re


class PayBillingVendor(models.Model):
    _name = 'pay.billing.vendor'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Pay Vendor Bill"
    _order = 'name desc, id desc'
    _check_company_auto = True


    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('done', 'Done'),
            ('cancel', 'Canceled'),
        ], 
        string='Status', 
        required=True,
        readonly=True,
        tracking=True,
        copy=False,
        default='draft',
    )
    READONLY_STATES = {
        'done': [('readonly', True)],
        'cancel': [('readonly', True)],
    }

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

    name = fields.Char(
        string='Document No.', 
        compute='_compute_name', 
        # required=True,
        store=True, 
        index=True, 
        readonly=True,
        tracking=True,
        # states=READONLY_STATES,
        copy=False,
    )

    company_id = fields.Many2one(
        comodel_name='res.company', 
        string='Company',
        store=True, 
        readonly=True,
        compute='_compute_company_id'
    )
    company_currency_id = fields.Many2one(string='Company Currency', readonly=True,
        related='company_id.currency_id')

    partner_id = fields.Many2one('res.partner', 
        string='Vendor', 
        required=True,
        readonly=False,
        tracking=True,
        domain="[('is_vendor','=',True)]",
        states=READONLY_STATES,
        check_company=True,
    )
    partner_address = fields.Char(
        string='Address', 
        related='partner_id.contact_address', 
        readonly=False,
    )

    user_id = fields.Many2one('res.users', 
        copy=False, 
        readonly=True,
        string='User',
        default=lambda self: self.env.user
    )

    document_date = fields.Date(
        string='Create Date', 
        required=True,
        index=True, 
        readonly=False, 
        states=READONLY_STATES,
        copy=False,
        default=fields.Date.context_today
    )
    document_date_due = fields.Date(
        string='Due Date', 
        index=True, 
        readonly=False, 
        states=READONLY_STATES,
        copy=False,
    )

    # === Reconciliation fields ===
    currency_id = fields.Many2one('res.currency', string='Currency', store=True, readonly=False,
        compute='_compute_currency_id',
        help="The payment's currency.")

    is_reconciled = fields.Boolean(string="Is Reconciled",
        store=True,
        compute='_compute_reconciliation_status',
        help="Technical field indicating if the payment is already reconciled.")
    is_matched = fields.Boolean(string="Is Matched With a Bank Statement",
        store=True,
        compute='_compute_reconciliation_status',
        help="Technical field indicating if the payment has been matched with a statement line.")

    # == Stat buttons ==
    reconciled_invoice_ids = fields.Many2many('account.move', string="Reconciled Invoices",
        compute='_compute_stat_buttons_from_reconciliation',
        help="Invoices whose journal items have been reconciled with these payments.")
    reconciled_invoices_count = fields.Integer(string="# Reconciled Invoices",
        compute="_compute_stat_buttons_from_reconciliation")
    reconciled_invoices_type = fields.Selection(
        [('credit_note', 'Credit Note'), ('invoice', 'Invoice')],
        compute='_compute_stat_buttons_from_reconciliation',
        help="Technical field used to determine label 'invoice' or 'credit note' in view")
    reconciled_bill_ids = fields.Many2many('account.move', string="Reconciled Bills",
        compute='_compute_stat_buttons_from_reconciliation',
        help="Invoices whose journal items have been reconciled with these payments.")
    reconciled_bills_count = fields.Integer(string="# Reconciled Bills",
        compute="_compute_stat_buttons_from_reconciliation")
    reconciled_statement_ids = fields.Many2many('account.bank.statement', string="Reconciled Statements",
        compute='_compute_stat_buttons_from_reconciliation',
        help="Statements matched to this payment")
    reconciled_statements_count = fields.Integer(string="# Reconciled Statements",
        compute="_compute_stat_buttons_from_reconciliation")

    # == Synchronized fields ==
    partner_type = fields.Selection([
            ('customer', 'Customer'),
            ('supplier', 'Vendor'),
        ],
        default='supplier',
        tracking=True,
        required=True,
        readonly=True
    )

    # === Journals fields ===
    bank_account_id = fields.Many2one('account.bank.account', 
        string='Bank Account', 
        tracking=True,
        required=True,
        readonly=False, 
        states=READONLY_STATES,
    )
    # @Add for Odoo15 process change
    outstanding_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Outstanding Account",
        store=True,
        related='bank_account_id.account_code', 
    )

    journal_id_domain = fields.One2many(
        'account.journal', 
        compute='_compute_journal_id_domain',
        store=False,
    )
    journal_id = fields.Many2one('account.journal', 
        string='Journal', 
        # domain="[('name','ilike','จ่ายชำระ')]",
        domain="[('id', 'in', journal_id_domain)]",
        tracking=True,
        required=True,
        readonly=False, 
        states=READONLY_STATES,
    )
    move_id = fields.Many2one('account.move', 
        string='Journal Entry', 
        tracking=True,
        readonly=True,
        copy=False,
    )

    # === Amount fields ===
    line_count = fields.Integer(
        string='Line Count',
        store=True,
        readonly=True,
        compute='_compute_amount',
    )
    amount_total = fields.Monetary(
        string='Total', 
        store=True, 
        readonly=True,
        tracking=True,
        currency_field='company_currency_id',
        compute='_compute_amount',
    )
    amount_total_text = fields.Char(
        string='Total Text',
        store=False,
        readonly=True,
        compute='_compute_amount_text',
    )

    line_ids = fields.One2many('pay.billing.vendor.line', 'pay_id', 
        string='Bill Items', 
        readonly=False, 
        states=READONLY_STATES,
        # copy=True,
    )

    reconcile_status = fields.Char(string='Reconcile', compute='_compute_reconcile_state')
    narration = fields.Html(string='Terms and Conditions')

    # @Sample method fields_view_get to modify view.
    # @api.model
    # def fields_view_get(self, view_id=None, view_type='tree', toolbar=False, submenu=False):
    #     res = super(ReceiptBillingCustomer, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
    #     if view_type == "tree":
    #         doc = etree.XML(res['arch'])
    #         for node in doc.xpath("//button[@name='button_open_bills']"):
    #             node.set('string', "Match")
    #         res['arch'] = etree.tostring(doc)
    #     return res


    @api.onchange('document_date', 'highest_name', 'company_id')
    def _onchange_document_date(self):
        if self.document_date:
            if (not self.document_date_due or self.document_date_due < self.document_date):
                self.document_date_due = self.document_date

    @api.onchange('partner_id')
    def _onchange_partner(self):
        if self.line_ids:
            self._recompute_dynamic_lines(self.partner_id)


    @api.depends('state')
    def _compute_journal_id_domain(self):
        for rec in self:
            journal_config = self.env['select.journal.config'].search([('form_select', '=', 'pay_billing_vendor')])
            rec.journal_id_domain = journal_config.journal_id

            if not rec.journal_id and rec.state == 'draft' and journal_config.journal_id:
                rec.journal_id = journal_config.filtered(lambda l: l.set_default == True).journal_id.id


    @api.depends('state', 'move_id')
    def _compute_name(self):
        for pay in self:
            if pay.state == 'draft' or not pay.move_id:
                pay.name = "/"
            else:
                pay.name = pay.move_id.name


    def _recompute_dynamic_lines(self, partner_id):
        for pay in self:
            # Dispatch lines and pre-compute some aggregated values.
            for line in pay.line_ids:
                if line.bill_id:
                    if line.bill_id.partner_id != partner_id:
                        raise Warning(_("Not match with ST Data."))


    @api.depends('line_ids')
    def _compute_amount(self):
        for pay in self:
            count = 0
            total = 0.0

            for line in pay.line_ids:
                count += 1
                total += line.balance

            pay.line_count = count
            pay.amount_total = total

    @api.depends('amount_total', 'company_currency_id')
    def _compute_amount_text(self):
        for pay in self:
            pay.amount_total_text = pay.company_currency_id.amount_to_text(pay.amount_total, "th_TH", "th")


    @api.depends('partner_id')
    def _compute_company_id(self):
        for pay in self:
            pay.company_id = pay.company_id or self.env.company


    def _get_bill_ref(self, line_ids):
        bill_ref = ''

        for line in line_ids:
            bill_ref += line.bill_id.name + ' '

        return bill_ref

    def action_done(self):
        for pay in self:
            vals = []
            for line in pay.line_ids:
                if line.balance >= 0:
                    debit = 0.0
                    credit = line.balance
                else:
                    debit = (-1) * line.balance
                    credit = 0.0
                vals.append(
                    (0, 0,
                        {
                            'account_id': pay.bank_account_id.account_code.id,
                            'partner_id': pay.partner_id.id,
                            'name': line.name,
                            'currency_id': pay.company_currency_id.id,
                            'debit': debit,
                            'credit': credit,
                        }
                    )
                )
                for deduct in line.deduct_ids:
                    if deduct.deduct_amount >= 0:
                        debit = 0.0
                        credit = deduct.deduct_amount
                    else:
                        debit = (-1) * deduct.deduct_amount
                        credit = 0.0
                    vals.append(
                        (0, 0,
                            {
                                'account_id': deduct.account_code.id,
                                'partner_id': pay.partner_id.id,
                                'name': line.name,
                                'currency_id': pay.company_currency_id.id,
                                'debit': debit,
                                'credit': credit,
                            }
                        )
                    )

                if line.pay >= 0:
                    debit = line.pay
                    credit = 0.0
                else:
                    debit = 0.0
                    credit = (-1) * line.pay
                vals.append(
                    (0, 0,
                        {
                            'account_id': pay.partner_id.property_account_payable_id.id,
                            'partner_id': pay.partner_id.id,
                            'name': line.name,
                            'currency_id': pay.company_currency_id.id,
                            'debit': debit,
                            'credit': credit,
                        }
                    )
                )

            move = self.env['account.move'].create({
                'move_type': 'entry',
                # 'date': pay.document_date,
                'partner_id': pay.partner_id.id,
                'journal_id': pay.journal_id.id,
                'currency_id': pay.company_currency_id.id,
                'line_ids': vals,
            })
            pay.move_id = move.id
            move.action_post()
            pay.state = 'done'


    def button_cancel(self):
        for pay in self:
            # @Revise to force cancel 'Journal Entry' and this 'Pay Vendor Bill'
            if pay.move_id:
                if pay.move_id.state == 'posted':
                    # raise UserError(_("Cannot cancel 'Pay Vendor Bill' that 'Journal Entry' already in Posted status."))
                    pay.move_id.button_draft()
                pay.move_id.button_cancel()

            # @Set line.bill_id.is_paid = False
            for line in pay.line_ids:
                line.bill_id.is_paid = False

            pay.state = 'cancel'


    # -------------------------------------------------------------------------
    # RECONCILIATION METHODS
    # -------------------------------------------------------------------------

    @api.depends('move_id.line_ids.matched_debit_ids', 'move_id.line_ids.matched_credit_ids')
    def _compute_stat_buttons_from_reconciliation(self):
        ''' Retrieve the invoices reconciled to the payments through the reconciliation (account.partial.reconcile). '''
        stored_payments = self.filtered('id')
        if not stored_payments:
            self.reconciled_invoice_ids = False
            self.reconciled_invoices_count = 0
            self.reconciled_invoices_type = ''
            self.reconciled_bill_ids = False
            self.reconciled_bills_count = 0
            self.reconciled_statement_ids = False
            self.reconciled_statements_count = 0
            return

        self.env['account.move'].flush()
        self.env['account.move.line'].flush()
        self.env['account.partial.reconcile'].flush()

        self._cr.execute('''
            SELECT
                payment.id,
                ARRAY_AGG(DISTINCT invoice.id) AS invoice_ids,
                invoice.move_type
            FROM pay_billing_vendor payment
            JOIN account_move move ON move.id = payment.move_id
            JOIN account_move_line line ON line.move_id = move.id
            JOIN account_partial_reconcile part ON
                part.debit_move_id = line.id
                OR
                part.credit_move_id = line.id
            JOIN account_move_line counterpart_line ON
                part.debit_move_id = counterpart_line.id
                OR
                part.credit_move_id = counterpart_line.id
            JOIN account_move invoice ON invoice.id = counterpart_line.move_id
            JOIN account_account account ON account.id = line.account_id
            WHERE account.internal_type IN ('receivable', 'payable')
                AND payment.id IN %(payment_ids)s
                AND line.id != counterpart_line.id
                AND invoice.move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt')
            GROUP BY payment.id, invoice.move_type
        ''', {
            'payment_ids': tuple(stored_payments.ids)
        })
        query_res = self._cr.dictfetchall()
        self.reconciled_invoice_ids = self.reconciled_invoices_count = False
        self.reconciled_bill_ids = self.reconciled_bills_count = False
        for res in query_res:
            pay = self.browse(res['id'])
            if res['move_type'] in self.env['account.move'].get_sale_types(True):
                pay.reconciled_invoice_ids += self.env['account.move'].browse(res.get('invoice_ids', []))
                pay.reconciled_invoices_count = len(res.get('invoice_ids', []))
            else:
                pay.reconciled_bill_ids += self.env['account.move'].browse(res.get('invoice_ids', []))
                pay.reconciled_bills_count = len(res.get('invoice_ids', []))

        self._cr.execute('''
            SELECT
                payment.id,
                ARRAY_AGG(DISTINCT counterpart_line.statement_id) AS statement_ids
            FROM pay_billing_vendor payment
            JOIN account_move move ON move.id = payment.move_id
            JOIN account_journal journal ON journal.id = move.journal_id
            JOIN account_move_line line ON line.move_id = move.id
            JOIN account_account account ON account.id = line.account_id
            JOIN account_partial_reconcile part ON
                part.debit_move_id = line.id
                OR
                part.credit_move_id = line.id
            JOIN account_move_line counterpart_line ON
                part.debit_move_id = counterpart_line.id
                OR
                part.credit_move_id = counterpart_line.id
            WHERE account.id = payment.outstanding_account_id
                AND payment.id IN %(payment_ids)s
                AND line.id != counterpart_line.id
                AND counterpart_line.statement_id IS NOT NULL
            GROUP BY payment.id
        ''', {
            'payment_ids': tuple(stored_payments.ids)
        })
        query_res = dict((payment_id, statement_ids) for payment_id, statement_ids in self._cr.fetchall())

        for pay in self:
            statement_ids = query_res.get(pay.id, [])
            pay.reconciled_statement_ids = [(6, 0, statement_ids)]
            pay.reconciled_statements_count = len(statement_ids)
            if len(pay.reconciled_invoice_ids.mapped('move_type')) == 1 and pay.reconciled_invoice_ids[0].move_type == 'out_refund':
                pay.reconciled_invoices_type = 'credit_note'
            else:
                pay.reconciled_invoices_type = 'invoice'

            # @Set line.bill_id.is_paid = False
            if pay.reconciled_bills_count == 0:
                for line in pay.line_ids:
                    line.bill_id.is_paid = False


    @api.depends('journal_id')
    def _compute_currency_id(self):
        for pay in self:
            pay.currency_id = pay.journal_id.currency_id or pay.journal_id.company_id.currency_id

    @api.depends('move_id.line_ids.amount_residual', 'move_id.line_ids.amount_residual_currency', 'move_id.line_ids.account_id')
    def _compute_reconciliation_status(self):
        ''' Compute the field indicating if the payments are already reconciled with something.
        This field is used for display purpose (e.g. display the 'reconcile' button redirecting to the reconciliation
        widget).
        '''
        for pay in self:
            liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

            if not pay.currency_id or not pay.id:
                pay.is_reconciled = False
                pay.is_matched = False
            elif pay.currency_id.is_zero(pay.amount_total):
                pay.is_reconciled = True
                pay.is_matched = True
            else:
                residual_field = 'amount_residual' if pay.currency_id == pay.company_id.currency_id else 'amount_residual_currency'
                if pay.journal_id.default_account_id and pay.journal_id.default_account_id in liquidity_lines.account_id:
                    # Allow user managing payments without any statement lines by using the bank account directly.
                    # In that case, the user manages transactions only using the register payment wizard.
                    pay.is_matched = True
                else:
                    pay.is_matched = pay.currency_id.is_zero(sum(liquidity_lines.mapped(residual_field)))

                reconcile_lines = (counterpart_lines + writeoff_lines).filtered(lambda line: line.account_id.reconcile)
                pay.is_reconciled = pay.currency_id.is_zero(sum(reconcile_lines.mapped(residual_field)))

                # @TODO For test match reconcile
                # print("=============================")
                # print("reconcile_lines : ", reconcile_lines)
                # print("residual_field : ", residual_field)
                # print("sum(reconcile_lines.mapped(residual_field)) : ", sum(reconcile_lines.mapped(residual_field)))


    @api.depends('state', 'reconciled_bills_count')
    def _compute_reconcile_state(self):
        for pay in self:
            if pay.state == 'done':
                if pay.reconciled_bills_count > 0:
                    pay.reconcile_state = 'reconciled'
                    pay.reconcile_status = '%s Bill' %(pay.reconciled_bills_count)
                else:
                    pay.reconcile_state = 'not_reconcile'
                    pay.reconcile_status = 'Payment Matching'
            else:
                pay.reconcile_state = 'not_reconcile'
                pay.reconcile_status = 'Draft' if pay.state == 'draft' else 'Cancelled'

    def action_open_manual_reconciliation_widget(self):
        ''' Open the manual reconciliation widget for the current payment.
        :return: A dictionary representing an action.
        '''
        self.ensure_one()

        if not self.partner_id:
            raise UserError(_("Payments without a vendor can't be matched"))

        liquidity_lines, counterpart_lines, writeoff_lines = self._seek_for_lines()

        action_context = {'company_ids': self.company_id.ids, 'partner_ids': self.partner_id.ids}
        if self.partner_type == 'customer':
            action_context.update({'mode': 'customers'})
        elif self.partner_type == 'supplier':
            action_context.update({'mode': 'suppliers'})

        if counterpart_lines:
            action_context.update({'move_line_id': counterpart_lines[0].id})

        return {
            'type': 'ir.actions.client',
            'tag': 'manual_reconciliation_view',
            'context': action_context,
        }

    def _seek_for_lines(self):
        ''' Helper used to dispatch the journal items between:
        - The lines using the temporary liquidity account.
        - The lines using the counterpart account.
        - The lines being the write-off lines.
        :return: (liquidity_lines, counterpart_lines, writeoff_lines)
        '''
        self.ensure_one()

        liquidity_lines = self.env['account.move.line']
        counterpart_lines = self.env['account.move.line']
        writeoff_lines = self.env['account.move.line']

        for line in self.move_id.line_ids:
            if line.account_id in self._get_valid_liquidity_accounts():
                liquidity_lines += line
            elif line.account_id.internal_type in ('receivable', 'payable') or line.partner_id == line.company_id.partner_id:
                counterpart_lines += line
            else:
                writeoff_lines += line

        return liquidity_lines, counterpart_lines, writeoff_lines

    def _get_valid_liquidity_accounts(self):
        return (
            self.bank_account_id.account_code,
            self.journal_id.default_account_id,
            # self.payment_method_line_id.payment_account_id,
            self.journal_id.company_id.account_journal_payment_debit_account_id,
            self.journal_id.company_id.account_journal_payment_credit_account_id,
            self.journal_id.inbound_payment_method_line_ids.payment_account_id,
            self.journal_id.outbound_payment_method_line_ids.payment_account_id,
        )

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def button_open_invoices(self):
        ''' Redirect the user to the invoice(s) paid by this payment.
        :return:    An action on account.move.
        '''
        self.ensure_one()

        action = {
            'name': _("Paid Invoices"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
        }
        if len(self.reconciled_invoice_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.reconciled_invoice_ids.id,
            })
        else:
            action.update({
                'view_mode': 'list,form',
                'domain': [('id', 'in', self.reconciled_invoice_ids.ids)],
            })
        return action

    def button_open_bills(self):
        ''' Redirect the user to the bill(s) paid by this payment.
        :return:    An action on account.move.
        '''
        self.ensure_one()

        action = {
            'name': _("Paid Bills"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
        }
        if len(self.reconciled_bill_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.reconciled_bill_ids.id,
            })
        else:
            action.update({
                'view_mode': 'list,form',
                'domain': [('id', 'in', self.reconciled_bill_ids.ids)],
            })
        return action

    def button_open_statements(self):
        ''' Redirect the user to the statement line(s) reconciled to this payment.
        :return:    An action on account.move.
        '''
        self.ensure_one()

        action = {
            'name': _("Matched Statements"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement',
            'context': {'create': False},
        }
        if len(self.reconciled_statement_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.reconciled_statement_ids.id,
            })
        else:
            action.update({
                'view_mode': 'list,form',
                'domain': [('id', 'in', self.reconciled_statement_ids.ids)],
            })
        return action

    def button_open_journal_entry(self):
        ''' Redirect the user to this payment journal.
        :return:    An action on account.move.
        '''
        self.ensure_one()
        return {
            'name': _("Journal Entry"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
            'view_mode': 'form',
            'res_id': self.move_id.id,
        }


    # def copy(self, default={}):
    #     default['name'] = "/"
    #     return super(PayBillingVendor, self).copy(default)

    def unlink(self):
        for record in self:
            if record.state == 'done':
                raise UserError(_("Cannot delete 'Pay Vendor Bill' that 'Status' in 'Done' status."))
        moves = self.with_context(force_delete=True).move_id
        res = super(PayBillingVendor, self).unlink()
        moves.unlink()
        return res



class PayBillingVendorLine(models.Model):
    _name = 'pay.billing.vendor.line'
    _description = "Pay Vendor Bill Line"
    _order = 'pay_name, id'
    _check_company_auto = True


    pay_id = fields.Many2one('pay.billing.vendor', 
        string='Pay Vendor Bill',
        index=True, 
        readonly=True, 
        # required=True, 
        auto_join=True, 
        ondelete="cascade",
        check_company=True,
        help="The pay of this entry line.")
    pay_name = fields.Char(string='Number', related='pay_id.name', store=True, index=True)

    bill_id_domain = fields.One2many(
        'account.billing.vendor', 
        compute='_compute_bill_id_domain',
        store=False,
    )
    bill_id = fields.Many2one('account.billing.vendor', 
        string='ST No.',
        index=True, 
        required=True, 
        domain="[('id', 'in', bill_id_domain)]",
        help="The bill of this entry line."
    )
    name = fields.Char(
        related='bill_id.name',
        string='Label',
    )

    company_id = fields.Many2one(related='pay_id.company_id', 
        store=True,
        readonly=True,
        # default=lambda self: self.env.company
    )
    company_currency_id = fields.Many2one(related='company_id.currency_id', 
        string='Company Currency',
        store=True,
        readonly=True, 
        help='Utility field to express amount currency')

    bill_date_due = fields.Date(
        string='ST Due Date', 
        related='bill_id.document_date_due', 
        readonly=True, 
    )

    bill_total = fields.Monetary(
        string='ST Amount Total', 
        related='bill_id.amount_total', 
        currency_field='company_currency_id',
        readonly=True,
    )
    bill_residual = fields.Monetary(
        string='ST Amount', 
        currency_field='company_currency_id',
    )

    # === Payment fields ===
    pay = fields.Monetary(
        string='Pay', 
        currency_field='company_currency_id',
    )
    amount = fields.Monetary(
        string='Amount', 
        currency_field='company_currency_id',
    )
    deducts = fields.Monetary(
        string='Deducts', 
        currency_field='company_currency_id',
        compute='_compute_balance', 
        store=True, 
        readonly=True,
    )
    balance = fields.Monetary(
        string='Balance', 
        currency_field='company_currency_id',
        compute='_compute_balance', 
        store=True, 
        readonly=True,
    )

    note = fields.Text(
        string='Note',
    )

    deduct_ids = fields.One2many('pay.billing.vendor.deduct', 'line_id', 
        string='Deduction Items', 
        copy=True, 
    )

    _sql_constraints = [
        ('key_unique', 'UNIQUE(pay_id, bill_id)', _("'ST No.' must be unique in Bill Line !")),
    ]


    @api.depends('pay_id')
    def _compute_bill_id_domain(self):
        for line in self:
            pay_partner_id = line.pay_id.partner_id.id or 0
            bill_ids = self.env['account.billing.vendor'].search([('partner_id','=',pay_partner_id),('state','=','done'),('is_paid','=',False)])

            # bill_ids._compute_payment_state()
            line.bill_id_domain = bill_ids.filtered(lambda l: l.payment_state != 'paid')

    # @Set balance = pay - deducts
    @api.depends('pay', 'deduct_ids.deduct_amount')
    def _compute_balance(self):
        for line in self:
            deducts = 0.0
            for deduct in line.deduct_ids:
                deducts += deduct.deduct_amount
            line.deducts = deducts
            line.balance = line.pay - deducts

    @api.onchange('amount')
    def _onchange_amount(self):
        for deduct in self.deduct_ids:
            if deduct.deduct_type == 'tax' and deduct.tax_id:
                if deduct.tax_id.amount_type != 'fixed':
                    deduct.deduct_amount = self.amount * deduct.tax_id.amount / 100

    @api.onchange('bill_id')
    def _onchange_bill_id(self):
        for line in self:
            line.bill_residual = line.bill_id.amount_residual



class PayBillingVendorDeduct(models.Model):
    _name = 'pay.billing.vendor.deduct'
    _description = "Pay Vendor Bill Deduct"


    line_id = fields.Many2one('pay.billing.vendor.line', 
        string='Pay Vendor Bill Line',
        index=True, 
        readonly=True, 
        required=True, 
        ondelete="cascade",
        help="The line of this deduction.")

    company_currency_id = fields.Many2one(related='line_id.company_currency_id', 
        string='Company Currency',
        store=True,
        readonly=True, 
        help='Utility field to express amount currency')

    # === Deduction fields ===
    deduct_type = fields.Selection(
        selection=[
            ('tax', 'Tax'),
            ('expend', 'Expend'),
        ], 
        string='Deduction Type', 
        required=True, 
        default='tax',
    )

    tax_id = fields.Many2one('account.tax', 
        string='Tax', 
        domain="[('active','=',True),('type_tax_use','=','purchase')]",
    )
    tax_amount_show = fields.Char(
        string='Tax Amount', 
    )

    account_code = fields.Many2one('account.account', 
        string='Account Code', 
        required=True, 
    )

    deduct_amount = fields.Monetary(
        string='Deduct Amount', 
        currency_field='company_currency_id',
    )

    # _sql_constraints = [
    #     ('key_unique', 'UNIQUE(line_id, account_code)', "'Account Code' must be unique in Deduction Line !"),
    # ]


    @api.onchange('tax_id')
    def _onchange_tax(self):
        if self.deduct_type == 'tax' and self.tax_id:
            account_tax = self.env['account.tax.repartition.line'].search([('invoice_tax_id', '=', self.tax_id.id),('repartition_type', '=', 'tax')], limit=1)
            self.account_code = account_tax.account_id
            if self.tax_id.amount_type == 'fixed':
                self.tax_amount_show = "{:,.2f}".format(self.tax_id.amount)
                self.deduct_amount = self.tax_id.amount
            else:
                self.tax_amount_show = "{:,.2f}%".format(self.tax_id.amount)
                self.deduct_amount = self.line_id.amount * self.tax_id.amount / 100

    @api.onchange('deduct_type')
    def _onchange_deduct_type(self):
        self.tax_id = False
        self.tax_amount_show = False
        self.account_code = False
        self.deduct_amount = 0.0

