# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SelectInvoice(models.TransientModel):
    _name = "wizard.select.invoice"
    _description = "Wizard Select Invoices"


    customer_bill_id = fields.Many2one('account.billing.customer', 
        string='Billing Note',
        readonly=True, 
        # required=True, 
        # ondelete="cascade",
    )
    # @Set to account.billing.customer only.
    # vendor_bill_id = fields.Many2one('account.billing.vendor', 
    vendor_bill_id = fields.Many2one('account.billing.customer', 
        string='Bill Acceptance',
        readonly=True, 
        # required=True, 
        # ondelete="cascade",
    )

    partner_id = fields.Many2one('res.partner', 
        required=True,
        readonly=True,
    )

    company_id = fields.Many2one(
        comodel_name='res.company', 
        string='Company',
        readonly=True,
        default=lambda self: self.env.company
    )
    company_currency_id = fields.Many2one(
        string='Company Currency', 
        readonly=True,
        related='company_id.currency_id'
    )

    all_invoice = fields.Boolean(
        string="All Invoice",
        default=True
    )
    from_invoice_date = fields.Date(
        string='From Invoice Date', 
        default=fields.Date.context_today
    )
    to_invoice_date = fields.Date(
        string='To Invoice Date', 
        default=fields.Date.context_today
    )

    invoice_items = fields.One2many('wizard.invoice.item', 'select_invoice_id', string='List of Invoice')
    message = fields.Char()


    def action_search(self):
        self.message = ""
        ok = True

        if not self.all_invoice:
            today = fields.Date.today()
            if not self.from_invoice_date:
                self.from_invoice_date = today
            if not self.to_invoice_date:
                self.to_invoice_date = today

            if not self.from_invoice_date or not self.to_invoice_date:
                self.message = _("Invalid Date value.")
                ok = False

            if self.from_invoice_date > self.to_invoice_date:
                self.message = _("Invalid Date value.")
                ok = False
        if not ok:
            raise UserError(self.message)

        if self.invoice_items:
            self.invoice_items.unlink()
        vals = []

        # if self.all_invoice:
        #     account_move = self.env['account.move'].search([('partner_id','=',self.partner_id.id),('move_type','=','out_invoice'),('state','=','posted'),('payment_state','=','not_paid')])
        # else:
        #     account_move = self.env['account.move'].search([('partner_id','=',self.partner_id.id),('move_type','=','out_invoice'),('state','=','posted'),('payment_state','=','not_paid'),('invoice_date','>=',self.from_invoice_date),('invoice_date','<=',self.to_invoice_date)])

        # for move in account_move:
        #     vals.append(
        #         (0, 0,
        #             {
        #                 'select_invoice_id': self.id,
        #                 'invoice_id': move.id,
        #             }
        #         )
        #     )

        if self.all_invoice:
            query_data = """
                SELECT am.id, abj.invoice_id, abj.state 
                FROM account_move am 
                LEFT JOIN 
                (SELECT abl.invoice_id, ab.state 
                    FROM {0} abl
                    INNER JOIN {1} ab 
                    ON ab.id = abl.bill_id AND ab.state='done'
                ) AS abj
                ON am.id = abj.invoice_id 
                WHERE TRUE 
                AND am.move_type = '{2}'
                AND am.state = 'posted'
                AND am.payment_state = 'not_paid'
                AND am.partner_id = %s
                AND abj.state IS NULL
                ORDER BY am.invoice_date, am.name ASC
            """
            if self.customer_bill_id and not self.vendor_bill_id:
                self._cr.execute(query_data.format("account_billing_customer_line", "account_billing_customer", "out_invoice"), (self.partner_id.id,))
                result = self._cr.dictfetchall()
            elif not self.customer_bill_id and self.vendor_bill_id:
                self._cr.execute(query_data.format("account_billing_vendor_line", "account_billing_vendor", "in_invoice"), (self.partner_id.id,))
                result = self._cr.dictfetchall()
            else:
                result = None

        else:
            query_data = """
                SELECT am.id, abj.invoice_id, abj.state 
                FROM account_move am 
                LEFT JOIN 
                (SELECT abl.invoice_id, ab.state 
                    FROM {0} abl
                    INNER JOIN {1} ab 
                    ON ab.id = abl.bill_id AND ab.state='done'
                ) AS abj
                ON am.id = abj.invoice_id 
                WHERE TRUE 
                AND am.move_type = '{2}'
                AND am.state = 'posted'
                AND am.payment_state = 'not_paid'
                AND am.partner_id = %s
                AND am.invoice_date >= %s
                AND am.invoice_date <= %s
                AND abj.state IS NULL
                ORDER BY am.invoice_date, am.name ASC
            """
            if self.customer_bill_id and not self.vendor_bill_id:
                self._cr.execute(query_data.format("account_billing_customer_line", "account_billing_customer", "out_invoice"), (self.partner_id.id, self.from_invoice_date, self.to_invoice_date))
                result = self._cr.dictfetchall()
            elif not self.customer_bill_id and self.vendor_bill_id:
                self._cr.execute(query_data.format("account_billing_vendor_line", "account_billing_vendor", "in_invoice"), (self.partner_id.id, self.from_invoice_date, self.to_invoice_date))
                result = self._cr.dictfetchall()
            else:
                result = None

        for data in result:
            vals.append(
                (0, 0,
                    {
                        'select_invoice_id': self.id,
                        'invoice_id': data['id'],
                    }
                )
            )
        self.update({'invoice_items': vals})

        return {
            "type": "ir.actions.act_window",
            "name": "Search Invoice Wizard",
            "res_model": "wizard.select.invoice",
            "views": [[False, "form"]],
            "target": "new",
            "res_id": self.id,
            # "context": dict(
            #     self.env.context,
            #     message = self.message,
            #     all_invoice = self.all_invoice,
            #     from_invoice_date = self.from_invoice_date,
            #     to_invoice_date = self.to_invoice_date,
            # ),
            # "is_deposit": True
        }


    def action_confirm(self):
        self.message = ""

        self.env.cr.execute(
            "DELETE FROM wizard_invoice_item WHERE select_invoice_id=%s AND select_item=FALSE", 
            (self.id,)
        )

        query_chk = """
            SELECT wii.select_invoice_id, wii.invoice_id, wii.select_item, ab.state 
            FROM wizard_invoice_item wii 
            INNER JOIN {0} abl
            ON wii.invoice_id = abl.invoice_id AND wii.select_invoice_id = %s
            AND wii.select_item = TRUE 
            INNER JOIN {1} ab 
            ON ab.id = abl.bill_id AND ab.state = 'done'
        """
        if self.customer_bill_id and not self.vendor_bill_id:
            self._cr.execute(query_chk.format("account_billing_customer_line", "account_billing_customer"), (self.id,))
            vals = self._cr.dictfetchall()
            if vals:
                self.message = _("Some Invoice/Bill in list is already Done. Please check again.")
                raise UserError(self.message)

            if self.customer_bill_id.line_ids:
                self.customer_bill_id.line_ids.unlink()

            vals = []
            for line in self.invoice_items:
                vals.append(
                    (0, 0,
                        {
                            'bill_id': self.customer_bill_id.id,
                            'invoice_id': line.invoice_id.id,
                        }
                    )
                )
            self.customer_bill_id.update({'line_ids': vals})

        elif not self.customer_bill_id and self.vendor_bill_id:
            self._cr.execute(query_chk.format("account_billing_vendor_line", "account_billing_vendor"), (self.id,))
            vals = self._cr.dictfetchall()
            if vals:
                self.message = _("Some Invoice/Bill in list is already Done. Please check again.")
                raise UserError(self.message)

            if self.vendor_bill_id.line_ids:
                self.vendor_bill_id.line_ids.unlink()

            vals = []
            for line in self.invoice_items:
                vals.append(
                    (0, 0,
                        {
                            'bill_id': self.vendor_bill_id.id,
                            'invoice_id': line.invoice_id.id,
                        }
                    )
                )
            self.vendor_bill_id.update({'line_ids': vals})

        else:
            self.message = _("Invalid Wizard Data.")
            raise UserError(self.message)


    # @api.model
    # def view_init(self, fields_list):
    #     # @SAMPLE for check field_list
    #     # print("fields_list : ", fields_list)
    #     # This will check before open Wizard.
    #     # raise UserError(str(fields_list))

    #     if self._context.get('default_customer_bill_id'):
    #         self.env.cr.execute(
    #             "DELETE FROM wizard_select_invoice WHERE customer_bill_id=%s", 
    #             (self._context.get('default_customer_bill_id'),)
    #         )
    #     if self._context.get('default_vendor_bill_id'):
    #         self.env.cr.execute(
    #             "DELETE FROM wizard_select_invoice WHERE vendor_bill_id=%s", 
    #             (self._context.get('default_vendor_bill_id'),)
    #         )


    @api.model
    def default_get(self, fields_list):
        result = super(SelectInvoice, self).default_get(fields_list)
        if (result.get('customer_bill_id') and result.get('vendor_bill_id')) or (not result.get('customer_bill_id') and not result.get('vendor_bill_id')):
            raise UserError(_("Invalid Wizard Data."))

        return result

