# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class AccountStockCard(models.Model):
    _name = 'account.stock.card'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Account Stock Card"
    _order = 'name desc, id desc'
    _check_company_auto = True

    @api.model
    def default_get(self, fields):
        res = super(AccountStockCard, self).default_get(fields)

        cost_line = []
        cost_line.append((0, 0, { 'cost_item': 'real_sale_price' }))
        cost_line.append((0, 0, { 'cost_item': 'import_duty' }))
        cost_line.append((0, 0, { 'cost_item': 'real_shipping' }))

        expenses_selling = []
        expenses_selling.append((0, 0, { 'cost_item': 'storage_costs' }))
        expenses_selling.append((0, 0, { 'cost_item': 'commission' }))
        expenses_selling.append((0, 0, { 'cost_item': 'before_delivering' }))
        expenses_selling.append((0, 0, { 'cost_item': 'ref_cost' }))
        expenses_selling.append((0, 0, { 'cost_item': 'pillow' }))
        expenses_selling.append((0, 0, { 'cost_item': 'premium' }))
        expenses_selling.append((0, 0, { 'cost_item': 'health_care' }))
        expenses_selling.append((0, 0, { 'cost_item': 'audio_equipment' }))
        expenses_selling.append((0, 0, { 'cost_item': 'forklift_fee' }))

        res.update({
            'cost_line_ids': cost_line,
            'expenses_selling_ids': expenses_selling,
        })

        return res

    name = fields.Char('Reference', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    car_order_id = fields.Many2one('car.order', string='ใบจอง', copy=False, required=True)
    date_receiving = fields.Char(string='วันที่รับรถเข้าสต๊อก', related='car_order_id.x_studio_estimated_delivery_date', copy=False)
    partner_id = fields.Many2one('res.partner', related='car_order_id.partner_id', string='ลูกค้า', copy=False, index=True)
    
    product_id = fields.Many2one('product.product', string="รถ", related='car_order_id.product_id', copy=False, index=True)
    car_model = fields.Char(string='รุ่นรถ', related='product_id.x_studio_model_vehicle', copy=False, index=True)
    chassis_number = fields.Char(string='หมายเลขตัวถัง', related='product_id.x_studio_chassis_no', copy=False, index=True)
    date_order = fields.Datetime(string='วันที่ขาย', default=fields.datetime.now(), required=True, index=True, copy=False)
    
    cost_line_ids = fields.One2many('account.stock.card.cost', 'stock_card_id', string='ต้นทุนจริง')
    expenses_selling_ids = fields.One2many('account.stock.card.expenses.selling', 'stock_card_id', string='ต้นทุนจริง')

    real_sale_price = fields.Float(compute='_compute_value_cost_line', string="ต้นทุนจริง ราคาตัวรถจริง", store=True)
    import_duty = fields.Float(compute='_compute_value_cost_line', string="ต้นทุนจริง ภาษีนำเข้า", store=True)
    real_shipping = fields.Float(compute='_compute_value_cost_line', string="ต้นทุนจริง ชิปปิ้งจ่ายจริง", store=True)

    total_car_cost = fields.Float(compute='_compute_total_car_cost', string="รวมราคาต้นทุนซื้อรถ", store=True)
    total_before_selling = fields.Float(compute='_compute_total_before_selling', string="รวมค่าใช้จ่ายก่อนการขายรถ", store=True)
    total_actual_cost = fields.Float(compute='_compute_calculate_cost', string="รวมต้นทุนจริง", store=True)
    actual_selling_price = fields.Float(related='car_order_id.sale_price', string="ราคาตั้ง / ราคาขายจริง", store=True)
    real_profit = fields.Float(compute='_compute_calculate_cost', string="กำไร(ขาดทุน)จริง", store=True)

    @api.depends('cost_line_ids.amount', 'car_order_id')
    def _compute_total_car_cost(self):
        for order in self:
            total = 0
            for line in order.cost_line_ids:
                total += line.amount

            order.total_car_cost = total

    @api.depends('cost_line_ids.amount', 'car_order_id')
    def _compute_value_cost_line(self):
        for order in self:
            real_sale_price = 0
            import_duty = 0
            real_shipping = 0
            for line in order.cost_line_ids:
                if line.cost_item == 'real_sale_price':
                    real_sale_price += line.amount
                if line.cost_item == 'import_duty':
                    import_duty += line.amount
                if line.cost_item == 'real_shipping':
                    real_shipping += line.amount

            order.real_sale_price = real_sale_price
            order.import_duty = import_duty
            order.real_shipping = real_shipping

    @api.depends('expenses_selling_ids.amount', 'car_order_id')
    def _compute_total_before_selling(self):
        for order in self:
            total = 0
            for line in order.expenses_selling_ids:
                total += line.amount

            order.total_before_selling = total

    @api.depends('total_car_cost', 'total_before_selling')
    def _compute_calculate_cost(self):
        for order in self:
            total_actual_cost = order.total_car_cost + order.total_before_selling
            real_profit = order.actual_selling_price - total_actual_cost

            order.total_actual_cost = total_actual_cost
            order.real_profit = real_profit

    @api.onchange('car_order_id')
    def onchange_car_order(self):
        if self.car_order_id:
            if self.cost_line_ids:
                for line in self.cost_line_ids:
                    if line.cost_item == 'real_sale_price':
                        line.amount = self.car_order_id.sale_price

            if self.expenses_selling_ids:
                for selling in self.expenses_selling_ids:
                    if selling.cost_item == 'commission':
                        selling.amount = self.car_order_id.commission_amount_total

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New') and vals.get('car_order_id'):
            car_order_id = self.env['car.order'].search([('id', '=', vals.get('car_order_id'))])
            product_id = car_order_id.product_id
            vals['name'] = self.env['ir.sequence'].next_by_code('account.stock.card') or _('New')

        return super(AccountStockCard, self).create(vals)
    
class AccountStockCardCostLine(models.Model):
    _name = 'account.stock.card.cost'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Account Stock Card Cost Line"
    _order = 'id asc'
    _check_company_auto = True

    stock_card_id = fields.Many2one('account.stock.card', string='Stock Card')
    cost_item = fields.Selection([
        ('real_sale_price', 'ราคาตัวรถจริง (ที่โอนไปต่างประเทศ)'),
        ('import_duty', 'ภาษีนำเข้า'),
        ('real_shipping', 'ชิปปิ้งจ่ายจริง'),
    ], string='รายการต้นทุนจริง', change_default=True)
    amount = fields.Float(string="Amount", required=True)

class AccountStockCardExpensesSelling(models.Model):
    _name = 'account.stock.card.expenses.selling'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Account Stock Card Expenses Selling"
    _order = 'id asc'
    _check_company_auto = True

    stock_card_id = fields.Many2one('account.stock.card', string='Stock Card')
    cost_item = fields.Selection([
        ('storage_costs', 'ค่าใช้จ่ายในการจัดเก็บสินค้าคงคลัง (จำนวนวันที่รถอยู่ในสต๊อกxอัตราดอกเบี้ย)'),
        ('commission', 'ค่า Commission'),
        ('before_delivering', 'ค่าใช้จ่ายในการเตรียมความพร้อมก่อนส่งมอบรถ'),
        ('ref_cost', 'ค่าแนะนำ'),
        ('pillow', 'หมอน B Autohaus'),
        ('premium', 'ค่าเบี้ยประกันภัย'),
        ('health_care', 'ค่า B Health Care Program'),
        ('audio_equipment', 'ค่าเครื่องเสียง'),
        ('forklift_fee', 'ค่ารถยก'),
    ], string='รายการค่าใช้จ่ายก่อนการขายรถ', change_default=True)
    amount = fields.Float(string="Amount", required=True)