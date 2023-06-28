from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CarOrderLine(models.Model):
    _name = "car.order.line"
    _description = "Car Order Line"

    product_id = fields.Many2one('product.product', string="สินค้า", required=True,
                                 domain="[('detailed_type', '=', 'service')]")
    price_company_header_1 = fields.Float(string="สั่งจ่ายในนามบริษัทที่ 1", default=0)
    price_company_header_2 = fields.Float(string="สั่งจ่ายในนามบริษัทที่ 2", default=0)
    price = fields.Float(compute="_compute_price")
    order_id = fields.Many2one('car.order')

    @api.depends('price_company_header_1', 'price_company_header_2')
    def _compute_price(self):
        for rec in self:
            rec.price = rec.price_company_header_1 + rec.price_company_header_2


class CarOrderCommission(models.Model):
    _name = "car.order.commission"
    _description = "Commission in Car Order"

    product_id = fields.Many2one('product.product', string="สินค้า", required=True)
    price = fields.Float("ราคา", required=True)
    order_id = fields.Many2one('car.order')


class CarOrderFreebie(models.Model):
    _name = "car.order.freebie"
    _description = "Freebie in Car Order"

    product_id = fields.Many2one('product.product', string="สินค้า", required=True)
    cost = fields.Float("Sales Cost", required=True, readonly=True)
    sale_price = fields.Float("Sale Price", required=True)
    order_id = fields.Many2one('car.order')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            standard_price = self.product_id.standard_price
            self.cost = standard_price
            self.sale_price = standard_price


class CarOrder(models.Model):
    _name = "car.order"
    _description = "Car Order"
    _order = 'date_order desc, id desc'

    name = fields.Char(string='Number', required=True, copy=False, readonly=True,
                       states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, index=True,
                       default=lambda self: _('New'))
    partner_id = fields.Many2one('res.partner', string='ลูกค้า', readonly=True,
                                 states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
                                 required=True, change_default=True,
                                 index=True, domain="[('type', '!=', 'private')]")
    partner_invoice_id = fields.Many2one('res.partner', string='ที่อยู่ใบแจ้งหนี้', readonly=True, required=True,
                                         states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
                                         domain="[('type', '!=', 'private')]")
    partner_shipping_id = fields.Many2one('res.partner', string='ที่อยู่สำหรับการจัดส่ง', readonly=True, required=True,
                                          states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
                                          domain="[('type', '!=', 'private')]")
    salesman_id = fields.Many2one('hr.employee', string="พนักงานขาย")
    date_order = fields.Datetime(string='วันที่ทำเอกสาร', default=fields.datetime.now(), required=True, readonly=True,
                                 index=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
                                 copy=False)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', required=True, readonly=True,
                                   states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    pricelist_price = fields.Float('ราคา Pricelist', compute="_compute_pricelist_price", store=True)
    currency_id = fields.Many2one(related='pricelist_id.currency_id', depends=["pricelist_id"], store=True,
                                  ondelete="restrict")
    payment_term_id = fields.Many2one('account.payment.term', string='เงื่อนไขการชำระเงิน', readonly=True, required=True,
                                      states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    product_id = fields.Many2one('product.product', string="รถ", domain="[('custom_fleet_ok', '=', True)]",
                                 required=True, readonly=True, index=True,
                                 states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    start_price = fields.Float(required=True, readonly=True, string="ราคาเปิดใบเสร็จ",
                               states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    sale_price = fields.Float(required=True, readonly=True, string="ราคาขาย",
                              states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    discount_price = fields.Float(required=True, readonly=True, string="ส่วนลด",
                              states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    reserve_price = fields.Float(required=True, readonly=True, string="เงินจอง",
                                 states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    company_header_1 = fields.Many2one('x_company_header', string='สั่งจ่ายในนามบริษัทที่ 1', readonly=True, required=True,
                                       states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    company_header_2 = fields.Many2one('x_company_header', string='สั่งจ่ายในนามบริษัทที่ 2', readonly=True, required=False,
                                       states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    # warranty
    number_of_years_warranty = fields.Integer(readonly=True, string="ปี",
                                              states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    number_of_distance_warranty = fields.Float(readonly=True, string="ระยะทาง", states={'draft': [('readonly', False)],
                                                                                        'confirm': [
                                                                                            ('readonly', False)]})
    value_of_warranty = fields.Float(readonly=True, string="เป็นเงินมลูค่า",
                                     states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    # detail line
    order_line = fields.One2many('car.order.line', 'order_id', readonly=True, string="รายการ",
                                 states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    amount_total = fields.Monetary(string='จำนวนเงินรวมทั้งสิ้น', store=True, compute='_amount_all')
    # finance
    finance_id = fields.Many2one('x_finance', readonly=True, string="ช่ือบริษัทไฟแนนซ์",
                                 states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    finance_amount = fields.Float(readonly=True, string="ยอดจัด",
                                  states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    finance_interest = fields.Float(readonly=True, string="ดอกเบี้ย",
                                    states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    finance_installment = fields.Float(readonly=True, string="งวดละ",
                                       states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    finance_number_of_installment = fields.Integer(readonly=True, string="จำนวนงวด", states={'draft': [('readonly', False)],
                                                                          'confirm': [('readonly', False)]})
    finance_commission = fields.Float(readonly=True, string="ค่าคอมจาก บ.ไฟแนนซ์",
                                      states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    # accessories
    acc_film_brand = fields.Char(readonly=True, string="ยี่ห้อ",
                                 states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    acc_film_front = fields.Integer(readonly=True, string="บานหน้า",
                                    states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    acc_film_around = fields.Integer(readonly=True, string="รอบคัน",
                                     states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    acc_film_roof = fields.Integer(readonly=True, string="หลังคา",
                                   states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    acc_film_other = fields.Char(readonly=True, string="อื่นๆ",
                                 states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    acc_sound_detail = fields.Char(readonly=True, string="รายละเอียด",
                                   states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    # commission and others
    commission_line = fields.One2many('car.order.commission', 'order_id', readonly=True, string="รายการ Commission",
                                      states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    commission_amount_total = fields.Monetary(string='รวมค่า Commission', store=True, compute='_commission_amount')
    # freebie
    freebie_line = fields.One2many('car.order.freebie', 'order_id', readonly=True, string="รายการของแถม",
                                      states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    freebie_amount_total = fields.Monetary(string='รวมค่าของแถม', store=True, compute='_freebie_amount')
    state = fields.Selection([
        ('draft', 'ใบเสนอราคา / ใบจอง'),
        ('confirm', 'รายละเอียดการขายรถยนตร์'),
        ('done', 'ยืนยันแล้ว'),
        ('cancel', 'ยกเลิก'),
    ], string='Status', readonly=True, default='draft')
    sale_id = fields.Many2one('sale.order', readonly=True, copy=False)
    invoice_count = fields.Integer(string='Invoice Count', compute='_get_invoiced')

    margin = fields.Monetary("Margin", compute='_compute_margin', store=True)
    margin_percent = fields.Char("Margin (%)", compute='_compute_margin', store=True)

    # ux field
    commission_product_categ = fields.Many2one('product.category', compute="_compute_commission_product_categ")

    def _compute_commission_product_categ(self):
        category = self.env['ir.config_parameter'].sudo().get_param('car_order_commission_product_category')
        for rec in self:
            rec.commission_product_categ = int(category)

    @api.model
    def default_get(self, field_list):
        result = super().default_get(field_list)
        result['x_studio_free_list'] = [
            (0, 0, {'x_name': "Warranty 2 ปี หรือ 50,000 กม."}),
            (0, 0, {'x_name': "ฟิล์มเซรามิค Blaupunkt"}),
            (0, 0, {'x_name': "ชุดพรมปูพื้น"}),
            (0, 0, {'x_name': "ชุดผ้ายางปูพื้น"}),
            (0, 0, {'x_name': "ขัดเคลือบสีก่อนส่งมอบ"}),
            (0, 0, {'x_name': "กรอบป้ายทะเบียน"}),
            (0, 0, {'x_name': "บัตร B card member club"}),
            (0, 0, {'x_name': "ส่วนลดค่าแรง 10% ค่าอะไหล่ 20%"}),
            (0, 0, {'x_name': "บริการRoadside Service 1 ครั้ง/ปี(เฉพาะกรุงเทพและปริมณฑล)"}),
            (0, 0, {'x_name': "บริการล้างรถฟรีเดือนละ1 ครั้ง"}),
            (0, 0, {'x_name': "Voucher ส่วนลด1,000 บาท"}),
            (0, 0, {'x_name': "Gift Set Premium วันส่งมอบรถ"}),
        ]
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)])
        if employee_id:
            result['salesman_id'] = employee_id
        return result

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
            price = 0.0
            if rec.product_id and rec.pricelist_id:
                item = rec.pricelist_id.item_ids.filtered(
                    lambda i: i.product_tmpl_id == rec.product_id.product_tmpl_id and (
                            not i.date_start or i.date_start <= rec.date_order) and (
                                      not i.date_end or i.date_end >= rec.date_order))
                if len(item) > 1:
                    raise ValidationError(_(f"Fond pricelist of {rec.product_id.name} more then one."))
                if item:
                    price = item.fixed_price
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

    @api.depends('freebie_line.sale_price')
    def _freebie_amount(self):
        for order in self:
            amount = 0
            for line in order.freebie_line:
                amount += line.sale_price
            order.update({
                'freebie_amount_total': amount
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

    @api.depends('pricelist_id', 'product_id', 'sale_price', 'discount_price', 'freebie_amount_total')
    def _compute_margin(self):
        for rec in self:
            margin, margin_percent = 0, 0
            if rec.pricelist_id and rec.pricelist_price:
                cost = rec.product_id.standard_price
                sale_price = rec.pricelist_price - rec.discount_price
                sale_price_after_freebie = sale_price - rec.freebie_amount_total
                margin = sale_price_after_freebie - cost
                margin_percent = round((margin / cost) * 100, 2)

            rec.margin = margin
            rec.margin_percent = str(margin_percent) + "%"

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
        for line in self.order_line.filtered(lambda i: i.product_id.is_car_order_expenses):
            order_line.append((0, 0, {
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

    def action_print_report(self):
        return self.env.ref('car_order.action_report_car_order').report_action(self)

    # report
    def _get_warranty_info(self):
        return f'ประกัน {self.number_of_years_warranty} ปี,   {self.number_of_distance_warranty} กม.'

    def _get_acc_film_other_info(self):
        return self.acc_film_other or '-'

    def copy_data(self, default=None):
        if default is None:
            default = {}
        if 'order_line' not in default:
            default['order_line'] = [(0, 0, line.copy_data()[0]) for line in self.order_line]
        if 'commission_line' not in default:
            default['commission_line'] = [(0, 0, line.copy_data()[0]) for line in self.commission_line]
        return super(CarOrder, self).copy_data(default)

    def action_update_cost(self):
        for rec in self:
            for freebie_id in rec.freebie_line:
                if freebie_id.product_id:
                    standard_price = freebie_id.product_id.standard_price
                    freebie_id.cost = standard_price
                    freebie_id.sale_price = standard_price
