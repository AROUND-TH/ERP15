# -*- coding: utf-8 -*-

import math
from odoo import _, models, fields, api
import datetime
import re
from odoo.tools.misc import formatLang, format_date, get_lang
from odoo.exceptions import UserError

from odoo.tools import float_round


class AccountMove(models.Model):
    _inherit = 'account.move'

    READONLY_STATES = {
        'posted': [('readonly', True)],
        'cancel': [('readonly', True)],
    }

    due_date = fields.Date(compute='_compute_due_date', string='Due Date')

    # === Asset Management Fields ===
    # Analytic
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tag', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    purchase_order_id = fields.Many2one('purchase.order', 
        string='Purchase Order', 
    )
    document_number = fields.Char(
        string='Document No.', 
    )
    invoice_date = fields.Date(string='Invoice/Bill Date', readonly=True, index=True, copy=False,
        states={'draft': [('readonly', False)]}, default=fields.Date.today())

    # @Override base field invoice_line_ids
    # /!\ invoice_line_ids is just a subset of line_ids.
    invoice_line_ids = fields.One2many('account.move.line', 'move_id', string='Invoice lines',
        copy=False, readonly=True,
        # domain=[('exclude_from_invoice_tab', '=', False)],
        domain=[('exclude_from_invoice_tab', '=', False), ('is_discount', '=', False)],
        states={'draft': [('readonly', False)]})

    # === Bill Discount Fields ===
    # bill_discount_percent = fields.Integer(
    bill_discount_percent = fields.Float(
        string='Discount %',
        digits='Product Price',
        states=READONLY_STATES,
    )
    bill_discount = fields.Monetary(
        string='Discount',
        states=READONLY_STATES,
    )
    amount_untaxed_nodiscount = fields.Monetary(
        string='Before Discount',
        store=True,
        compute='_compute_amount',
    )
    # =================================

    narration_notes = fields.Text(string='notes')


    # === Bill Discount Functions ===
    @api.onchange('bill_discount_percent')
    def _onchange_bill_discount_percent(self):
        if self.bill_discount_percent > 0:
            bill_discount_percent = float_round(self.bill_discount_percent, precision_digits=2)
            bill_discount = self.amount_untaxed_nodiscount * (bill_discount_percent / 100)
            if bill_discount >= self.amount_untaxed_nodiscount:
                self.bill_discount_percent = 100
                self.bill_discount = self.amount_untaxed_nodiscount
            else:
                self.bill_discount_percent = bill_discount_percent
                self.bill_discount = bill_discount
        else:
            self.bill_discount_percent = 0
            # self.bill_discount = 0.0

    @api.onchange('bill_discount')
    def _onchange_bill_discount(self):
        if self.bill_discount > 0.0:
            bill_discount = float_round(self.bill_discount, precision_digits=2)
            if bill_discount >= self.amount_untaxed_nodiscount:
                self.bill_discount_percent = 100
                self.bill_discount = self.amount_untaxed_nodiscount
            else:
                self.bill_discount = bill_discount
        else:
            self.bill_discount = 0.0

        if self.bill_discount_percent > 0:
            bill_discount = self.amount_untaxed_nodiscount * (self.bill_discount_percent / 100)
            bill_discount = float_round(bill_discount, precision_digits=2)

            if bill_discount != self.bill_discount:
                self.bill_discount_percent = 0

    # @Override compute method _compute_amount
    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id',
        'bill_discount')
    def _compute_amount(self):
        self.set_bill_discount()

        super(AccountMove, self)._compute_amount()
        for move in self:
            if move.move_type != 'out_invoice' or move.state == 'posted':
                continue

            bill_discount = move.bill_discount

            move.amount_untaxed_nodiscount = move.amount_untaxed + move.bill_discount
            # move._onchange_currency()

            move._onchange_bill_discount_percent()

            if bill_discount != move.bill_discount and move.amount_untaxed > 0:
                move.set_bill_discount()
                super(AccountMove, move)._compute_amount()
                move.amount_untaxed_nodiscount = move.amount_untaxed + move.bill_discount


    def ceil(self, number1, number2):
        return math.ceil(number1 / number2)

    def _get_total_amount_untaxed(self):
        total = 0
        for line in self.invoice_line_ids:
            if not line.tax_ids:
                total += line.price_subtotal

        return total

    def _get_total_amount_taxed(self):
        total = 0
        for line in self.invoice_line_ids:
            if line.tax_ids:
                total += line.price_subtotal

        return total

    def set_bill_discount(self):
        sale_discount_account_id = int(self.env['ir.config_parameter'].sudo().get_param('sale_discount_account_id'))
        if not sale_discount_account_id:
            raise UserError(_('Discount Account ID is not set. Please contact Administrator.'))

        for move in self:
            if move.move_type != 'out_invoice' or move.state == 'posted':
                continue

            if not move.bill_discount:
                line_discount = move.line_ids.filtered(lambda r: r.account_id.id == sale_discount_account_id)
                if line_discount:
                    line_discount.update({
                        'is_discount': True,
                        'amount_currency': 0.0,
                    })
                    move.line_ids._onchange_amount_currency()
                    move._recompute_dynamic_lines(recompute_all_taxes=True)
            else:
                taxes = []
                invoice_line_taxes = move.invoice_line_ids.filtered(lambda r: r.account_id.id != sale_discount_account_id and r.tax_ids != False)
                for invoice_line in invoice_line_taxes:
                    taxes.extend(invoice_line.tax_ids.ids)
                taxes = list(set(taxes))

                line_discount = move.line_ids.filtered(lambda r: r.account_id.id == sale_discount_account_id)
                if line_discount:
                    line_discount.update({
                        'is_discount': True,
                        'amount_currency': move.bill_discount,
                        'tax_ids': [(6, 0, taxes)],
                    })

                else:
                    move.update({
                        'line_ids': [(0, 0, {
                            'move_id': move.id,
                            'account_id': sale_discount_account_id,
                            'partner_id': move.partner_id.id,
                            'is_discount': True,
                            'currency_id': move.currency_id.id,
                            'amount_currency': move.bill_discount,
                            'tax_ids': [(6, 0, taxes)],
                        })],
                    })

                move.line_ids._onchange_amount_currency()
                move._recompute_dynamic_lines(recompute_all_taxes=True)


    def final_clear_bill_discount(self):
        sale_discount_account_id = int(self.env['ir.config_parameter'].sudo().get_param('sale_discount_account_id'))
        if not sale_discount_account_id:
            raise UserError(_('Discount Account ID is not set. Please contact Administrator.'))

        for move in self:
            if move.move_type != 'out_invoice':
                continue

            if not move.bill_discount:
                line_discount = move.line_ids.filtered(lambda r: r.account_id.id == sale_discount_account_id)
                if line_discount:
                    line_discount.with_context(check_move_validity=False).unlink()
            else:
                line_discount = move.line_ids.filtered(lambda r: r.account_id.id == sale_discount_account_id)
                num = 1
                if len(line_discount) > num:
                    i = 0
                    for line in line_discount:
                        i += 1
                        if i > num:
                            line.with_context(check_move_validity=False).unlink()

    # =================================


    @api.onchange('invoice_date', 'highest_name', 'company_id')
    def _onchange_invoice_date(self):
        super(AccountMove, self)._compute_tax_lock_date_message()
        if self.invoice_date:
            if not self.invoice_payment_term_id and (not self.invoice_date_due or self.invoice_date_due < self.invoice_date):
                self.invoice_date_due = self.invoice_date

            accounting_date = self.invoice_date
            if accounting_date != self.date:
                self.date = accounting_date
                self._onchange_currency()
            else:
                self._onchange_recompute_dynamic_lines()

    @api.depends("invoice_date", "invoice_payment_term_id")
    def _compute_due_date(self):
        for rec in self:
            if rec.invoice_date and rec.invoice_payment_term_id:
                days = 0
                if rec.invoice_payment_term_id:
                    for term_line in rec.invoice_payment_term_id.line_ids:
                        if term_line.option == 'day_after_invoice_date':
                            days = term_line.days
                
                due_date = rec.invoice_date + datetime.timedelta(days=days)
                rec.due_date = due_date
            else:
                rec.due_date = False

    def _get_reversal_invoice(self, reversal_invoice):

        reversal_amount_total = 0
        if reversal_invoice:
            reversal = re.split(': |, ',reversal_invoice)
            move_id = self.env['account.move'].search([('name', '=', reversal[1])])

            if move_id:
                reversal_amount_total = move_id.amount_total
        
        return reversal_amount_total

    def _get_report_journal_filename(self):
        filename = self.journal_id.name

        return filename


    @api.model_create_multi
    def create(self, vals_list):
        result = super(AccountMove, self).create(vals_list)
        result.final_clear_bill_discount()
        return result

    def write(self, vals):
        result = super(AccountMove, self).write(vals)
        self.final_clear_bill_discount()
        return result


    def _format_date_text_th(self, date):
        date_splits = str(date).split('-')
        year = int(date_splits[0]) + 543
        month = self._month_to_text_th(date_splits[1])

        return date_splits[2] + ' ' + month + ' ' + str(year)

    def _month_to_text_th(self, month):
        month_character = ''

        if month == '01':
            month_character = 'ม.ค.'
        elif month == '02':
            month_character = 'ก.พ.'
        elif month == '03':
            month_character = 'มี.ค.'
        elif month == '04':
            month_character = 'เม.ย.'
        elif month == '05':
            month_character = 'พ.ค.'
        elif month == '06':
            month_character = 'มิ.ย.'
        elif month == '07':
            month_character = 'ก.ค.'
        elif month == '08':
            month_character = 'ส.ค.'
        elif month == '09':
            month_character = 'ก.ย.'
        elif month == '10':
            month_character = 'ต.ค.'
        elif month == '11':
            month_character = 'พ.ย.'
        else:
            month_character = 'ธ.ค.'

        return month_character


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    asset_count = fields.Integer(string='Asset', default=0)
    tax_audit_amount = fields.Monetary(compute="_compute_tax_audit_amount", string="Tax Audit")

    is_discount = fields.Boolean(
        default=False,
        copy=True,
        help="Technical field used to exclude discount lines from the invoice_line_ids tab in the form view."
    )


    @api.depends('tax_tag_ids', 'debit', 'credit', 'journal_id', 'tax_tag_invert')
    def _compute_tax_audit_amount(self):
        for record in self:
            tax_audit_amount = 0
            for tag in record.tax_tag_ids:
                tax_audit_amount = (record.tax_tag_invert and -1 or 1) * (tag.tax_negate and -1 or 1) * record.balance

            record.tax_audit_amount = tax_audit_amount
            