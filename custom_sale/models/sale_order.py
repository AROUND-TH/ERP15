# -*- coding: utf-8 -*-

from odoo import api, fields, models

from odoo.tools import float_round


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _prepare_procurement_values(self, group_id=False):
        values = super(SaleOrderLine, self)._prepare_procurement_values(group_id)
        self.ensure_one()
        if self.new_delivery_date:
            return values
        date_planned = self.order_id.commitment_date or self.order_id.expected_date
        values.update({
            'date_planned': date_planned,
            'date_deadline': date_planned
        })
        return values


class SaleOrder(models.Model):
    _inherit = "sale.order"

    READONLY_STATES = {
        'done': [('readonly', True)],
        'cancel': [('readonly', True)],
    }

    credit_limit = fields.Float(string='Credit Limit', compute="_compute_credit", store=True)
    credit_balance = fields.Float(string='Credit Balance', compute="_compute_credit", store=True)
    credit_available = fields.Float(string="Credit Available", compute="_compute_credit", store=True)
    transportation = fields.Char(string="Transportation")
    port_of_loading = fields.Char(string="Port of Loading")
    port_of_destination = fields.Char(string="Port of Destination")

    bank_id = fields.Many2one('account.bank.account', string="Bank Account", required=True)

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
        compute='_amount_all',
    )
    # =================================


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

    # @Override compute method _amount_all
    @api.depends('order_line.price_total', 'bill_discount')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            amount_untaxed = amount_tax = 0.0
            amount_have_tax = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
                if line.price_tax > 0.0:
                    amount_have_tax += line.price_subtotal

            bill_discount_percent = order.bill_discount_percent
            bill_discount = order.bill_discount
            amount_untaxed_nodiscount = amount_untaxed
            if amount_untaxed_nodiscount != order.amount_untaxed_nodiscount:
                if bill_discount_percent > 0:
                    bill_discount_percent = float_round(bill_discount_percent, precision_digits=2)
                    bill_discount = amount_untaxed_nodiscount * (bill_discount_percent / 100)
                    bill_discount = float_round(bill_discount, precision_digits=2)
                    if bill_discount >= amount_untaxed_nodiscount:
                        bill_discount_percent = 100
                        bill_discount = amount_untaxed_nodiscount
                else:
                    bill_discount_percent = 0

            amount_untaxed = amount_untaxed - bill_discount
            sub_amount_tax = (amount_tax * bill_discount) / amount_have_tax if amount_have_tax else 0.0
            amount_tax = amount_tax - sub_amount_tax
            amount_tax = float_round(amount_tax, precision_digits=2, rounding_method='DOWN')

            order.update({
                'bill_discount_percent': bill_discount_percent,
                'bill_discount': bill_discount,
                'amount_untaxed_nodiscount': amount_untaxed_nodiscount,
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax,
            })
    # =================================

    # @Override method _prepare_invoice
    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()

        invoice_vals["bill_discount_percent"] = self.bill_discount_percent
        invoice_vals["bill_discount"] = self.bill_discount

        return invoice_vals


    @api.model
    def default_get(self, fields):
         res = super().default_get(fields)
         bank_id = self.env['account.bank.account'].sudo().search([], limit=1)
         if bank_id:
             res.update({'bank_id': bank_id.id})
         return res

    @api.onchange('partner_id')
    def _onchange_partner_id_incoterm(self):
        if not self.partner_id:
            return

        self.incoterm = self.partner_id.incoterm_id
        self.transportation = self.partner_id.transportation
        self.port_of_loading = self.partner_id.port_of_loading
        self.port_of_destination = self.partner_id.port_of_destination

    @api.depends('partner_id.property_payment_term_id', 'partner_id.credit_limit', 'partner_id.credit', 'amount_total')
    def _compute_credit(self):
        for rec in self:
            partner_id = rec.partner_id
            if rec.state not in ['draft', 'sent'] or not partner_id:
                continue
            credit_limit, credit_balance, credit_available = 0, 0, 0
            if partner_id.credit_limit:
                credit_limit = partner_id.credit_limit
                credit_balance = credit_limit - partner_id.credit
                credit_available = credit_balance - rec.amount_total
            rec.credit_limit = credit_limit
            rec.credit_balance = credit_balance
            rec.credit_available = credit_available
    
    def _action_cancel(self):
        documents = None
        for sale_order in self:
            if sale_order.state == 'sale' and sale_order.order_line:
                sale_order_lines_quantities = {order_line: (order_line.product_uom_qty, 0) for order_line in sale_order.order_line}
                documents = self.env['stock.picking'].with_context(include_draft_documents=True)._log_activity_get_documents(sale_order_lines_quantities, 'move_ids', 'UP')
        picking_ids_rec = self.picking_ids.filtered(lambda p: p.state != 'done')
        for picking in picking_ids_rec:
            picking.action_cancel()
        if documents:
            filtered_documents = {}
            for (parent, responsible), rendering_context in documents.items():
                if parent._name == 'stock.picking':
                    if parent.state == 'cancel':
                        continue
                filtered_documents[(parent, responsible)] = rendering_context
            self._log_decrease_ordered_quantity(filtered_documents, cancel=True)
        return super()._action_cancel()

