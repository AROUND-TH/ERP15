# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning, UserError, ValidationError

from collections import defaultdict

import re


class AccountBillingVendor(models.Model):
    _name = 'account.billing.vendor'
    _inherit = ['sequence.mixin']
    _description = "Bill Acceptance"
    _order = 'date desc, name desc, id desc'
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
        copy=False, 
        default='draft',
    )
    READONLY_STATES = {
        'done': [('readonly', True)],
        'cancel': [('readonly', True)],
    }

    payment_state = fields.Selection(
        selection=[
            ('not_paid', 'Not Paid'),
            ('partial', 'Partially Paid'),
            ('paid', 'Paid'),
        ], 
        string='Payment Status', 
        compute='_compute_payment_state', 
        store=False,
        readonly=True, 
        default='not_paid',
    )
    is_paid = fields.Boolean(
        string="Is Paid",
        copy=False,
        default=False,
        help="Technical field to check Billing Note is already paid."
    )

    name = fields.Char(
        string='Document No.', 
        compute='_compute_name', 
        required=True,
        store=True, 
        index=True, 
        readonly=False, 
        states=READONLY_STATES,
        copy=False, 
    )
    highest_name = fields.Char(compute='_compute_highest_name')
    show_name_warning = fields.Boolean(store=False)
    date = fields.Date(
        string='Date',
        required=True,
        index=True,
        readonly=True,
        copy=False,
        default=fields.Date.context_today
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
        domain="[('is_vender','=',True)]",
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
        currency_field='company_currency_id',
        compute='_compute_amount',
    )
    amount_total_text = fields.Char(
        string='Total Text',
        store=False,
        readonly=True,
        compute='_compute_amount_text',
    )
    amount_residual = fields.Monetary(
        string='Amount Due', 
        readonly=True,
        currency_field='company_currency_id',
        compute='_compute_amount_residual'
    )

    line_ids = fields.One2many('account.billing.vendor.line', 'bill_id', 
        string='Invoice/Bill Items', 
        readonly=False, 
        states=READONLY_STATES,
        copy=True, 
    )

    narration = fields.Html(string='Terms and Conditions')


    @api.onchange('document_date', 'highest_name', 'company_id')
    def _onchange_document_date(self):
        if self.document_date:
            if (not self.document_date_due or self.document_date_due < self.document_date):
                self.document_date_due = self.document_date
            if self.document_date != self.date:
                self.date = self.document_date

        if self.state == 'draft' and self.name != '/':
            self.name = '/'

    @api.onchange('partner_id')
    def _onchange_partner(self):
        # if self.state == 'draft' and self._get_last_sequence() and self.name and self.name != '/':
        #     self.name = '/'
        if self.state == 'draft' and self.name != '/':
            self.name = '/'

        if self.line_ids:
            self._recompute_dynamic_lines(self.partner_id)


    @api.depends('state', 'date')
    def _compute_name(self):
        def billing_key(bill):
            return (bill)

        def date_key(bill):
            return (bill.date.year, bill.date.month)

        grouped = defaultdict(  # key: bill
            lambda: defaultdict(  # key: first adjacent (date.year, date.month)
                lambda: {
                    'records': self.env['account.billing.vendor'],
                    'format': False,
                    'format_values': False,
                    'reset': False
                }
            )
        )
        self = self.sorted(lambda m: (m.date, m.id))
        highest_name = self[0]._get_last_sequence() if self else False

        # Group the bill by billing and month
        for bill in self:
            if not highest_name and bill == self[0] and bill.state != 'done' and bill.date:
                # In the form view, we need to compute a default sequence so that the user can edit
                # it. We only check the first bill as an approximation (enough for new in form view)
                pass
            elif (bill.name and bill.name != '/') or bill.state != 'done':
                try:
                    if bill.state != 'done':
                        bill._constrains_date_sequence()
                    # Has already a name or is not posted, we don't add to a batch
                    continue
                except ValidationError:
                    # Has never been posted and the name doesn't match the date: recompute it
                    pass
            group = grouped[billing_key(bill)][date_key(bill)]
            if not group['records']:
                # Compute all the values needed to sequence this whole group
                bill._set_next_sequence()
                group['format'], group['format_values'] = bill._get_sequence_format_param(bill.name)
                group['reset'] = bill._deduce_sequence_number_reset(bill.name)
            group['records'] += bill

        # Fusion the groups depending on the sequence reset and the format used because `seq` is
        # the same counter for multiple groups that might be spread in multiple months.
        final_batches = []
        for billing_group in grouped.values():
            billing_group_changed = True
            for date_group in billing_group.values():
                if (
                    billing_group_changed
                    or final_batches[-1]['format'] != date_group['format']
                    or dict(final_batches[-1]['format_values'], seq=0) != dict(date_group['format_values'], seq=0)
                ):
                    final_batches += [date_group]
                    billing_group_changed = False
                elif date_group['reset'] == 'never':
                    final_batches[-1]['records'] += date_group['records']
                elif (
                    date_group['reset'] == 'year'
                    and final_batches[-1]['records'][0].date.year == date_group['records'][0].date.year
                ):
                    final_batches[-1]['records'] += date_group['records']
                else:
                    final_batches += [date_group]

        # Give the name based on previously computed values
        for batch in final_batches:
            for bill in batch['records']:
                bill.name = batch['format'].format(**batch['format_values'])
                batch['format_values']['seq'] += 1
            batch['records']._compute_split_sequence()

        self.filtered(lambda m: not m.name).name = '/'


    # @api.depends('partner_id', 'date')
    @api.depends('company_id', 'date')
    def _compute_highest_name(self):
        for record in self:
            record.highest_name = record._get_last_sequence()

    def _get_last_sequence_domain(self, relaxed=False):
        self.ensure_one()

        # if not self.date or not self.partner_id:
        if not self.date or not self.company_id:
            return "WHERE FALSE", {}

        # where_string = "WHERE partner_id = %(partner_id)s AND name != '/'"
        # param = {'partner_id': self.partner_id.id}
        where_string = "WHERE company_id = %(company_id)s AND name != '/'"
        param = {'company_id': self.company_id.id}

        if not relaxed:
            # domain = [('partner_id', '=', self.partner_id.id), ('id', '!=', self.id or self._origin.id), ('name', 'not in', ('/', '', False))]
            domain = [('company_id', '=', self.company_id.id), ('id', '!=', self.id or self._origin.id), ('name', 'not in', ('/', '', False))]

            reference_bill_name = self.search(domain + [('date', '<=', self.date)], order='date desc', limit=1).name
            if not reference_bill_name:
                reference_bill_name = self.search(domain, order='date asc', limit=1).name
            sequence_number_reset = self._deduce_sequence_number_reset(reference_bill_name)
            if sequence_number_reset == 'year':
                where_string += " AND date_trunc('year', date::timestamp without time zone) = date_trunc('year', %(date)s) "
                param['date'] = self.date
                param['anti_regex'] = re.sub(r"\?P<\w+>", "?:", self._sequence_monthly_regex.split('(?P<seq>')[0]) + '$'
            elif sequence_number_reset == 'month':
                where_string += " AND date_trunc('month', date::timestamp without time zone) = date_trunc('month', %(date)s) "
                param['date'] = self.date
            else:
                param['anti_regex'] = re.sub(r"\?P<\w+>", "?:", self._sequence_yearly_regex.split('(?P<seq>')[0]) + '$'

            if param.get('anti_regex'):
                where_string += " AND sequence_prefix !~ %(anti_regex)s "

        return where_string, param

    def _get_starting_sequence(self):
        self.ensure_one()
        starting_sequence = "%s/%04d/%02d/0000" % ("ST", self.date.year, self.date.month)
        return starting_sequence

    @api.onchange('name', 'highest_name')
    def _onchange_name_warning(self):
        if self.name and self.name != '/' and self.name <= (self.highest_name or ''):
            self.show_name_warning = True
        else:
            self.show_name_warning = False

        origin_name = self._origin.name
        if not origin_name or origin_name == '/':
            origin_name = self.highest_name or ''
        if self.name and self.name != '/' and origin_name and origin_name != '/':
            format, format_values = self._get_sequence_format_param(self.name)
            origin_format, origin_format_values = self._get_sequence_format_param(origin_name)

            if (
                format != origin_format
                or dict(format_values, seq=0) != dict(origin_format_values, seq=0)
            ):
                changed = _(
                    "It was previously '%(previous)s' and it is now '%(current)s'.",
                    previous=origin_name,
                    current=self.name,
                )
                reset = self._deduce_sequence_number_reset(self.name)
                if reset == 'month':
                    detected = _(
                        "The sequence will restart at 1 at the start of every month.\n"
                        "The year detected here is '%(year)s' and the month is '%(month)s'.\n"
                        "The incrementing number in this case is '%(formatted_seq)s'."
                    )
                elif reset == 'year':
                    detected = _(
                        "The sequence will restart at 1 at the start of every year.\n"
                        "The year detected here is '%(year)s'.\n"
                        "The incrementing number in this case is '%(formatted_seq)s'."
                    )
                else:
                    detected = _(
                        "The sequence will never restart.\n"
                        "The incrementing number in this case is '%(formatted_seq)s'."
                    )
                format_values['formatted_seq'] = "{seq:0{seq_length}d}".format(**format_values)
                detected = detected % format_values
                return {'warning': {
                    'title': _("The sequence format has changed."),
                    'message': "%s\n\n%s" % (changed, detected)
                }}

    # @api.onchange('partner_id', 'line_ids', 'document_date_due')
    # def _onchange_recompute_dynamic_lines(self):
    #     if self.line_ids:
    #         self._recompute_dynamic_lines(self.partner_id)

    def _recompute_dynamic_lines(self, partner_id):
        ''' Recompute all lines that depend of others.

        For example, tax lines depends of base lines (lines having tax_ids set). This is also the case of cash rounding
        lines that depend of base lines or tax lines depending the cash rounding strategy. When a payment term is set,
        this method will auto-balance the move with payment term lines.
        '''

        # warning = False
        for bill in self:
            # Dispatch lines and pre-compute some aggregated values.
            for line in bill.line_ids:
                if line.invoice_id:
                    if line.invoice_id.partner_id != partner_id:
                        # line.unlink()
                        # warning = True

                        raise Warning(_("Not match with Vendor Bill."))

        #     bill.partner_id = partner_id
        # if warning:
        #     raise Warning(_("Not match with Vendor Bill."))


    # @api.depends('line_ids.amount_total')
    @api.depends('line_ids')
    def _compute_amount(self):
        for bill in self:
            count = 0
            total = 0.0

            for line in bill.line_ids:
                count += 1
                total += line.amount_total

            bill.line_count = count
            bill.amount_total = total

    @api.depends('amount_total', 'company_currency_id')
    def _compute_amount_text(self):
        for bill in self:
            # bill.amount_total_text = bill.company_currency_id.with_context({'lang': 'th_TH'}).amount_to_text(bill.amount_total, "context", "core")
            # bill.amount_total_text = bill.company_currency_id.amount_to_text(bill.amount_total, "context", "core")
            bill.amount_total_text = bill.company_currency_id.amount_to_text(bill.amount_total, "th_TH", "th")

    @api.depends('line_ids')
    def _compute_amount_residual(self):
        for bill in self:
            residual = 0.0

            for line in bill.line_ids:
                residual += line.amount_residual

            bill.amount_residual = residual

    @api.depends('state', 'is_paid')
    def _compute_payment_state(self):
        for bill in self:
            if bill.state == 'done':
                # @Activate check cancel reconcile and set is_paid = False
                pay_line_ids = self.env['pay.billing.vendor.line'].search([('bill_id', '=', bill.id)])
                pay_line_ids.filtered(lambda l: l.pay_id.reconciled_bills_count == 0)

                if bill.is_paid:
                    bill.payment_state = 'paid'
                else:
                    if bill.amount_residual <= 0:
                        bill.payment_state = 'paid'
                        bill.is_paid = True
                    elif bill.amount_residual < bill.amount_total:
                        bill.payment_state = 'partial'
                    else:
                        bill.payment_state = 'not_paid'
            else:
                bill.payment_state = 'not_paid'
                # bill.is_paid = False

    @api.depends('partner_id')
    def _compute_company_id(self):
        for bill in self:
            bill.company_id = bill.company_id or self.env.company

    def action_done(self):
        for bill in self:
            if not bill.line_ids:
                raise UserError(_("You need to add a line before done."))

            query_chk = """
                SELECT abl.bill_id, abl.invoice_id, abj.state 
                FROM account_billing_vendor_line abl
                LEFT JOIN 
                (SELECT abl.bill_id, abl.invoice_id, ab.state 
                    FROM account_billing_vendor_line abl
                    INNER JOIN account_billing_vendor ab 
                    ON ab.id = abl.bill_id 
                    AND ab.state = 'done'
                ) AS abj
                ON abl.invoice_id = abj.invoice_id
                WHERE abl.bill_id = %s
                AND abj.state = 'done'
            """
            self._cr.execute(query_chk, (bill.id,))
            vals = self._cr.dictfetchall()
            if vals:
                raise UserError(_("Some Invoice/Bill in list is already Done. Please check again."))

            bill.state = 'done'
            # @Set invoice->payment_reference to this document name.
            for line in bill.line_ids:
                line.invoice_id.payment_reference = bill.name

    def button_cancel(self):
        for bill in self:
            if bill.payment_state != 'not_paid':
                raise UserError(_("Cannot cancel 'Bill Acceptance' that 'Payment Status' not in 'Not Paid' status."))
            else:
                bill.state = 'cancel'
                # @Set is_paid = False
                bill.is_paid = False
                # @Set invoice->payment_reference to default (invoice number).
                for line in bill.line_ids:
                    line.invoice_id.payment_reference = line.invoice_id.name

    def button_select_invoice(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Search Invoice Wizard",
            "res_model": "wizard.select.invoice",
            "views": [[False, "form"]],
            "target": "new",
            "context": {
                'default_vendor_bill_id': self.id,
                'default_partner_id': self.partner_id.id,
            },
            "is_deposit": True
        }


    def copy(self, default={}):
        default['name'] = "/"
        return super(AccountBillingVendor, self).copy(default)

    def unlink(self):
        for record in self:
            if record.state == 'done':
                raise UserError(_("Cannot delete 'Bill Acceptance' that 'Status' in 'Done' status."))
        return super(AccountBillingVendor, self).unlink()



class AccountBillingVendorLine(models.Model):
    _name = 'account.billing.vendor.line'
    _description = "Bill Acceptance Line"
    _order = 'date, bill_name, id'
    _check_company_auto = True


    bill_id = fields.Many2one('account.billing.vendor', 
        string='Bill Acceptance',
        index=True, 
        readonly=True, 
        # required=True, 
        auto_join=True, 
        ondelete="cascade",
        check_company=True,
        help="The bill of this entry line.")
    bill_name = fields.Char(string='Number', related='bill_id.name', store=True, index=True)
    date = fields.Date(related='bill_id.date', store=True, readonly=True, index=True, copy=False, group_operator='min')

    bill_partner_domain = fields.Integer(
        compute='_compute_bill_partner_domain', 
    )

    invoice_id = fields.Many2one('account.move', 
        string='Invoice/Bill No.',
        index=True, 
        required=True, 
        domain="[('partner_id','=',bill_partner_domain),('move_type','=','in_invoice'),('state','=','posted'),('payment_state','=','not_paid')]",
        # check_company=True,
        help="The move of this entry line."
    )
    name = fields.Char(
        related='invoice_id.name',
        string='Label',
    )

    company_id = fields.Many2one(related='bill_id.company_id', 
        store=True,
        readonly=True,
        # default=lambda self: self.env.company
    )
    company_currency_id = fields.Many2one(related='company_id.currency_id', 
        string='Company Currency',
        store=True,
        readonly=True, 
        help='Utility field to express amount currency')

    invoice_date = fields.Date(
        string='Invoice/Bill Date', 
        related='invoice_id.invoice_date', 
        readonly=True, 
    )
    invoice_date_due = fields.Date(
        string='Due Date', 
        related='invoice_id.due_date', 
        readonly=True, 
    )

    # === Amount fields ===
    amount_untaxed = fields.Monetary(
        string='Untaxed Amount', 
        related='invoice_id.amount_untaxed', 
        currency_field='company_currency_id',
        store=True, 
        readonly=True, 
    )
    amount_tax = fields.Monetary(
        string='Tax', 
        related='invoice_id.amount_tax', 
        currency_field='company_currency_id',
        store=True, 
        readonly=True,
    )
    amount_total = fields.Monetary(
        string='Total', 
        related='invoice_id.amount_total', 
        currency_field='company_currency_id',
        store=True, 
        readonly=True,
    )
    amount_residual = fields.Monetary(
        string='Amount Due', 
        related='invoice_id.amount_residual', 
        currency_field='company_currency_id',
        readonly=True,
    )

    note = fields.Text(
        string='Note', 
        readonly=False,
    )

    _sql_constraints = [
        ('key_unique', 'UNIQUE(bill_id, invoice_id)', _("'Invoice/Bill No.' must be unique in Bill Line !")),
    ]


    # @api.onchange('invoice_id')
    # def _onchange_invoice(self):
    #     res = {'domain': {'invoice_id': [('partner_id','=',0),('move_type','=','in_invoice'),('state','=','posted'),('payment_state','=','not_paid')]}}
    #     if self.invoice_id or self.bill_id.partner_id:
    #         res['domain']['invoice_id'] = [('partner_id','=',self.bill_id.partner_id.id),('move_type','=','in_invoice'),('state','=','posted'),('payment_state','=','not_paid')]
    #     return res


    @api.depends('bill_id')
    def _compute_bill_partner_domain(self):
        for line in self:
            line.bill_partner_domain = line.bill_id.partner_id.id or 0

