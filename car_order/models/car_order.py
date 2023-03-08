from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CarOrderLine(models.Model):
    _name = "car.order.line"
    _description = "Car Order Line"

    product_id = fields.Many2one('product.product', required=True, domain="[('detailed_type', '=', 'service')]")
    price_company_header_1 = fields.Float(string="Company 1", default=0)
    price_company_header_2 = fields.Float(string="Company 2", default=0)
    price = fields.Float(compute="_compute_price")
    order_id = fields.Many2one('car.order')

    @api.depends('price_company_header_1', 'price_company_header_2')
    def _compute_price(self):
        for rec in self:
            rec.price = rec.price_company_header_1 + rec.price_company_header_2


class CarOrderCommission(models.Model):
    _name = "car.order.commission"
    _description = "Commission in Car Order"

    product_id = fields.Many2one('product.product', required=True, domain="[('detailed_type', '=', 'service')]")
    price = fields.Float(required=True)
    order_id = fields.Many2one('car.order')


class CarOrder(models.Model):
    _name = "car.order"
    _description = "Car Order"
    _order = 'date_order desc, id desc'

    name = fields.Char(string='Number', required=True, copy=False, readonly=True,
                       states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True,
                                 states={'draft': [('readonly', False)]}, required=True, change_default=True,
                                 index=True, domain="[('type', '!=', 'private')]")
    partner_invoice_id = fields.Many2one('res.partner', string='Invoice Address', readonly=True, required=True,
                                         states={'draft': [('readonly', False)]}, domain="[('type', '!=', 'private')]")
    partner_shipping_id = fields.Many2one('res.partner', string='Delivery Address', readonly=True, required=True,
                                          states={'draft': [('readonly', False)]}, domain="[('type', '!=', 'private')]")
    date_order = fields.Datetime(string='Order Date', default=fields.datetime.now(), required=True, readonly=True,
                                 index=True, states={'draft': [('readonly', False)]}, copy=False)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', required=True, readonly=True,
                                   states={'draft': [('readonly', False)]})
    currency_id = fields.Many2one(related='pricelist_id.currency_id', depends=["pricelist_id"], store=True,
                                  ondelete="restrict")
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms', readonly=True, required=True,
                                      states={'draft': [('readonly', False)]})
    product_id = fields.Many2one('product.product', string="Car", domain="[('custom_fleet_ok', '=', True)]",
                                 required=True, readonly=True, index=True, states={'draft': [('readonly', False)]},
                                 copy=False)
    start_price = fields.Float(required=True, readonly=True, states={'draft': [('readonly', False)]}, copy=False)
    sale_price = fields.Float(required=True, readonly=True, states={'draft': [('readonly', False)]}, copy=False)
    reserve_price = fields.Float(required=True, readonly=True, states={'draft': [('readonly', False)]}, copy=False)
    company_header_1 = fields.Many2one('x_company_header', string='Company 1', readonly=True, required=True,
                                       states={'draft': [('readonly', False)]})
    company_header_2 = fields.Many2one('x_company_header', string='Company 2', readonly=True, required=False,
                                       states={'draft': [('readonly', False)]})
    # warranty
    number_of_years_warranty = fields.Integer()
    number_of_distance_warranty = fields.Float()
    value_of_warranty = fields.Float()
    # detail line
    order_line = fields.One2many('car.order.line', 'order_id', readonly=True, states={'draft': [('readonly', False)]})
    amount_total = fields.Monetary(string='Total', store=True, compute='_amount_all')
    # finance
    finance_id = fields.Many2one('x_finance', readonly=True, states={'draft': [('readonly', False)]})
    finance_amount = fields.Float(readonly=True, states={'draft': [('readonly', False)]})
    finance_interest = fields.Float(readonly=True, states={'draft': [('readonly', False)]})
    finance_installment = fields.Float(readonly=True, states={'draft': [('readonly', False)]})
    finance_commission = fields.Float(readonly=True, states={'draft': [('readonly', False)]})
    # accessories
    acc_film_brand = fields.Char(readonly=True, states={'draft': [('readonly', False)]})
    acc_film_front = fields.Integer(readonly=True, states={'draft': [('readonly', False)]})
    acc_film_around = fields.Integer(readonly=True, states={'draft': [('readonly', False)]})
    acc_film_roof = fields.Integer(readonly=True, states={'draft': [('readonly', False)]})
    acc_film_other = fields.Char(readonly=True, states={'draft': [('readonly', False)]})
    acc_sound_detail = fields.Char(readonly=True, states={'draft': [('readonly', False)]})
    # commission and others
    commission_line = fields.One2many('car.order.commission', 'order_id', readonly=True,
                                      states={'draft': [('readonly', False)]})
    commission_amount_total = fields.Monetary(string='Total', store=True, compute='_commission_amount')

    state = fields.Selection([
        ('draft', 'Quotation'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, default='draft')
    sale_id = fields.Many2one('sale.order', readonly=True)
    invoice_count = fields.Integer(string='Invoice Count', compute='_get_invoiced')

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """
        Update the following fields when the partner is changed:
        - Pricelist
        - Payment terms
        - Invoice address
        - Delivery address
        """
        if not self.partner_id:
            self.update({
                'partner_invoice_id': False,
                'partner_shipping_id': False
            })
            return

        addr = self.partner_id.address_get(['delivery', 'invoice'])
        values = {
            'pricelist_id': self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.id or False,
            'payment_term_id': self.partner_id.property_payment_term_id and self.partner_id.property_payment_term_id.id or False,
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
        }
        self.update(values)

    @api.depends('order_line.price_company_header_1', 'order_line.price_company_header_2')
    def _amount_all(self):
        for order in self:
            amount = 0
            for line in order.order_line:
                amount += line.price
            order.update({
                'amount_total': amount
            })

    @api.depends('commission_line.price')
    def _commission_amount(self):
        for order in self:
            amount = 0
            for line in order.commission_line:
                amount += line.price
            order.update({
                'commission_amount_total': amount
            })

    @api.model
    def create(self, vals):
        seq_date = None
        if 'date_order' in vals:
            seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date_order']))
        vals['name'] = self.env['ir.sequence'].next_by_code('car.order', sequence_date=seq_date) or _('New')
        return super().create(vals)

    def action_done(self):
        order_line = [(0, 0, {
            'product_id': self.product_id.id,
            'price_unit': self.sale_price
        })]
        for line in self.order_line:
            order_line.append((0,0, {
                'product_id': line.product_id.id,
                'price_unit': line.price
            }))
        sale_id = self.env['sale.order'].create({
            "car_order_id": self.id,
            "partner_id": self.partner_id.id,
            "partner_invoice_id": self.partner_invoice_id.id,
            "partner_shipping_id": self.partner_shipping_id.id,
            "pricelist_id": self.pricelist_id.id,
            "payment_term_id": self.payment_term_id.id,
            "order_line": order_line
        })
        self.sale_id = sale_id
        sale_id.action_confirm()
        self.state = "done"

    def action_cancel(self):
        self.state = "cancel"

    @api.depends('sale_id.invoice_count')
    def _get_invoiced(self):
        for rec in self:
            rec.invoice_count = rec.sale_id.invoice_count

    def action_view_sale(self):
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_orders")
        form_view = [(self.env.ref('sale.view_order_form').id, 'form')]
        if 'views' in action:
            action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
        else:
            action['views'] = form_view
        action['res_id'] = self.sale_id.id
        return action

    def action_view_invoice(self):
        return self.sale_id.action_view_invoice()
