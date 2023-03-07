# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.float_utils import float_compare

# Available values for the release_to_pay field.
_release_to_pay_status_list = [('yes', 'Yes'), ('no', 'No'), ('exception', 'Exception')]

class AccountMove(models.Model):
    _inherit = 'account.move'

    release_to_pay_manual = fields.Selection(
        _release_to_pay_status_list,
        string='Should Be Paid',
        default='yes',
        help="  * Yes: you should pay the bill, you have received the products\n"
             "  * No, you should not pay the bill, you have not received the products\n"
             "  * Exception, there is a difference between received and billed quantities\n"
             "This status is defined automatically, but you can force it by ticking the 'Force Status' checkbox.")

    @api.depends('invoice_line_ids.can_be_paid', 'force_release_to_pay', 'payment_state')
    def _compute_release_to_pay(self):
        records = self
        if self.env.context.get('module') == 'account_3way_match':
            # on module installation we set 'no' for all paid bills and other non relevant records at once
            records = records.filtered(lambda r: r.payment_state != 'paid' and r.move_type in ('in_invoice', 'in_refund'))
            (self - records).release_to_pay = 'no'
        for invoice in records:
            if invoice.payment_state == 'paid':
                # no need to pay, if it's already paid
                invoice.release_to_pay = 'no'
            elif invoice.force_release_to_pay:
                #we must use the manual value contained in release_to_pay_manual
                invoice.release_to_pay = invoice.release_to_pay_manual
            else:
                #otherwise we must compute the field
                result = None
                for invoice_line in invoice.invoice_line_ids:
                    line_status = invoice_line.can_be_paid
                    if line_status == 'exception':
                        #If one line is in exception, the entire bill is
                        result = 'exception'
                        break
                    elif not result:
                        result = line_status
                    elif line_status != result:
                        result = 'exception'
                        break
                    #The last two elif conditions model the fact that a
                    #bill will be in exception if its lines have different status.
                    #Otherwise, its status will be the one all its lines share.

                #'result' can be None if the bill was entirely empty.
                invoice.release_to_pay = invoice.release_to_pay_manual = result or 'yes'