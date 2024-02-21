# -*- coding: utf-8 -*-

from odoo import _, models, fields, api
import datetime
import re
from odoo.tools.misc import formatLang, format_date, get_lang
from odoo.exceptions import UserError
import locale

class AccountMove(models.Model):
    _inherit = 'account.move'


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

    narration_notes = fields.Text(string='notes')
    company_for_report_id = fields.Many2one(comodel_name='res.company', string='Company')


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

    def format_monetary_without_currency(self, value):
        locale.setlocale(locale.LC_ALL, '')  # Set the locale to the user's default

        # Get the formatting information for the current locale
        conv = locale.localeconv()

        # Convert the value to a string representation with the appropriate formatting
        formatted_value = locale.format_string("%s%.*f", (conv['positive_sign'], conv['frac_digits'], value), grouping=True)
        return formatted_value


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    asset_count = fields.Integer(string='Asset', default=0)
    tax_audit_amount = fields.Monetary(compute="_compute_tax_audit_amount", string="Tax Audit")


    @api.depends('tax_tag_ids', 'debit', 'credit', 'journal_id', 'tax_tag_invert')
    def _compute_tax_audit_amount(self):
        for record in self:
            tax_audit_amount = 0
            for tag in record.tax_tag_ids:
                tax_audit_amount = (record.tax_tag_invert and -1 or 1) * (tag.tax_negate and -1 or 1) * record.balance

            record.tax_audit_amount = tax_audit_amount
            