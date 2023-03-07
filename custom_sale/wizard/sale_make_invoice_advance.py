# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"


    # @Override method _prepare_invoice_values
    def _prepare_invoice_values(self, order, name, amount, so_line):
        invoice_vals = super(SaleAdvancePaymentInv, self)._prepare_invoice_values(order, name, amount, so_line)

        invoice_vals["bill_discount_percent"] = order.bill_discount_percent
        invoice_vals["bill_discount"] = order.bill_discount

        return invoice_vals

