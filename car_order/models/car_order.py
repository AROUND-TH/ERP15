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
                       states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, index=True,
                       default=lambda self: _('New'))
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True,
                                 states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
                                 required=True, change_default=True,
                                 index=True, domain="[('type', '!=', 'private')]")
    partner_invoice_id = fields.Many2one('res.partner', string='Invoice Address', readonly=True, required=True,
                                         states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
                                         domain="[('type', '!=', 'private')]")
    partner_shipping_id = fields.Many2one('res.partner', string='Delivery Address', readonly=True, required=True,
                                          states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
                                          domain="[('type', '!=', 'private')]")
    date_order = fields.Datetime(string='Order Date', default=fields.datetime.now(), required=True, readonly=True,
                                 index=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
                                 copy=False)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', required=True, readonly=True,
                                   states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    pricelist_price = fields.Char('Pricelist Price', compute="_compute_pricelist_price", store=True)
    currency_id = fields.Many2one(related='pricelist_id.currency_id', depends=["pricelist_id"], store=True,
                                  ondelete="restrict")
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms', readonly=True, required=True,
                                      states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    product_id = fields.Many2one('product.product', string="Car", domain="[('custom_fleet_ok', '=', True)]",
                                 required=True, readonly=True, index=True,
                                 states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
                                 copy=False)
    start_price = fields.Float(required=True, readonly=True,
                               states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, copy=False)
    sale_price = fields.Float(required=True, readonly=True,
                              states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, copy=False)
    reserve_price = fields.Float(required=True, readonly=True,
                                 states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, copy=False)
    company_header_1 = fields.Many2one('x_company_header', string='Company 1', readonly=True, required=True,
                                       states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    company_header_2 = fields.Many2one('x_company_header', string='Company 2', readonly=True, required=False,
                                       states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    # warranty
    number_of_years_warranty = fields.Integer(readonly=True,
                                              states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    number_of_distance_warranty = fields.Float(readonly=True, states={'draft': [('readonly', False)],
                                                                      'confirm': [('readonly', False)]})
    value_of_warranty = fields.Float(readonly=True,
                                     states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    # detail line
    order_line = fields.One2many('car.order.line', 'order_id', readonly=True,
                                 states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    amount_total = fields.Monetary(string='Premium', store=True, compute='_amount_all')
    # finance
    finance_id = fields.Many2one('x_finance', readonly=True,
                                 states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    finance_amount = fields.Float(readonly=True,
                                  states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    finance_interest = fields.Float(readonly=True,
                                    states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    finance_installment = fields.Float(readonly=True,
                                       states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    finance_commission = fields.Float(readonly=True,
                                      states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    # accessories
    acc_film_brand = fields.Char(readonly=True,
                                 states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    acc_film_front = fields.Integer(readonly=True,
                                    states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    acc_film_around = fields.Integer(readonly=True,
                                     states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    acc_film_roof = fields.Integer(readonly=True,
                                   states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    acc_film_other = fields.Char(readonly=True,
                                 states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    acc_sound_detail = fields.Char(readonly=True,
                                   states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    # commission and others
    commission_line = fields.One2many('car.order.commission', 'order_id', readonly=True,
                                      states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    commission_amount_total = fields.Monetary(string='Total', store=True, compute='_commission_amount')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, default='draft')
    sale_id = fields.Many2one('sale.order', readonly=True)
    invoice_count = fields.Integer(string='Invoice Count', compute='_get_invoiced')

    margin = fields.Monetary("Margin", compute='_compute_margin', store=True)
    margin_percent = fields.Float("Margin (%)", compute='_compute_margin', store=True)

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
        property_product_pricelist = self.partner_id.property_product_pricelist
        property_payment_term_id = self.partner_id.property_payment_term_id
        values = {
            'pricelist_id': property_product_pricelist and property_product_pricelist.id or False,
            'payment_term_id': property_payment_term_id and property_payment_term_id.id or False,
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
        }
        self.update(values)

    @api.depends('pricelist_id', 'product_id', 'date_order')
    def _compute_pricelist_price(self):
        for rec in self:
            price = "-"
            if rec.product_id and rec.pricelist_id:
                item = rec.pricelist_id.item_ids.filtered(
                    lambda i: i.product_tmpl_id == rec.product_id.product_tmpl_id and (
                            not i.date_start or i.date_start <= rec.date_order) and (
                                      not i.date_end or i.date_end >= rec.date_order))
                if len(item) > 1:
                    raise ValidationError(_(f"Fond pricelist of {rec.product_id.name} more then one."))
                if item:
                    price = item.price
            rec.pricelist_price = price

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

    def _convert_purchase_price(self, product_cost, from_uom):
        self.ensure_one()
        if not product_cost:
            return product_cost
        from_currency = self.product_id.cost_currency_id
        to_cur = self.currency_id
        to_uom = self.product_id.uom_id
        if to_uom and to_uom != from_uom:
            product_cost = from_uom._compute_price(
                product_cost,
                to_uom,
            )
        return from_currency._convert(
            from_amount=product_cost,
            to_currency=to_cur,
            company=self.env.company,
            date=self.date_order or fields.Date.today(),
            round=False,
        ) if to_cur and product_cost else product_cost

    def _get_purchase_price(self):
        self.ensure_one()
        purchase_price = 0.0
        if not self.product_id:
            return purchase_price
        # car
        purchase_price = self._convert_purchase_price(self.product_id.standard_price, self.product_id.uom_id)
        # premium
        for line in self.order_line:
            purchase_price += self._convert_purchase_price(line.product_id.standard_price, line.product_id.uom_id)
        return purchase_price

    @api.depends('product_id', 'sale_price', 'partner_shipping_id', 'order_line', 'order_line.price')
    def _compute_margin(self):
        for rec in self:
            margin, margin_percent = 0, 0
            if rec.product_id and rec.partner_shipping_id:
                qty = 1
                taxes = self.product_id.taxes_id.compute_all(price_unit=rec.sale_price, currency=rec.currency_id,
                                                             product=rec.product_id, partner=rec.partner_shipping_id)
                price_subtotal = taxes['total_excluded']
                # find margin
                margin = price_subtotal - (rec._get_purchase_price() * qty)
                margin_percent = price_subtotal and margin / price_subtotal
            rec.margin = margin
            rec.margin_percent = margin_percent

    @api.model
    def create(self, vals):
        seq_date = None
        if 'date_order' in vals:
            seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date_order']))
        vals['name'] = self.env['ir.sequence'].next_by_code('car.order', sequence_date=seq_date) or _('New')
        return super().create(vals)

    def action_confirm(self):
        if self.state != "draft":
            raise ValidationError(_('Status must be "Draft".'))
        self.state = "confirm"

    def action_done(self):
        if self.state != "confirm":
            raise ValidationError(_('Status must be "Confirm".'))
        order_line = [(0, 0, {
            'product_id': self.product_id.id,
            'price_unit': self.sale_price
        })]
        for line in self.order_line:
            order_line.append((0, 0, {
                'product_id': line.product_id.id,
                'price_unit': 0
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
        if self.sale_id:
            self.sale_id.action_cancel()
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
