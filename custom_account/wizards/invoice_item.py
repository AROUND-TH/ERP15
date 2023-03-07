# -*- coding: utf-8 -*-

from odoo import api, fields, models


class InvoiceItem(models.TransientModel):
    _name = 'wizard.invoice.item'
    _description = "Wizard Invoice Items"


    select_invoice_id = fields.Many2one('wizard.select.invoice', 
        readonly=True, 
        ondelete="cascade",
    )

    select_item = fields.Boolean(
        string="Select",
        default=False
    )
    invoice_id = fields.Many2one('account.move', 
        string='Invoice/Bill No.',
        required=True, 
    )

    company_id = fields.Many2one(
        related='select_invoice_id.company_id', 
        readonly=True, 
        # default=lambda self: self.env.company
    )
    company_currency_id = fields.Many2one(
        related='company_id.currency_id', 
        string='Company Currency',
        readonly=True, 
    )

    invoice_date = fields.Date(
        string='Invoice/Bill Date', 
        related='invoice_id.invoice_date', 
        readonly=True, 
    )
    invoice_date_due = fields.Date(
        string='Due Date', 
        related='invoice_id.invoice_date_due', 
        readonly=True, 
    )

    # === Amount fields ===
    amount_untaxed = fields.Monetary(
        string='Untaxed Amount', 
        related='invoice_id.amount_untaxed', 
        currency_field='company_currency_id',
        readonly=True, 
    )
    amount_tax = fields.Monetary(
        string='Tax', 
        related='invoice_id.amount_tax', 
        currency_field='company_currency_id',
        readonly=True,
    )
    amount_total = fields.Monetary(
        string='Total', 
        related='invoice_id.amount_total', 
        currency_field='company_currency_id',
        readonly=True,
    )

