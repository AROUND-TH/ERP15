from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_truckscale = fields.Boolean(string='Truck Scale',
        help="เงื่อนไขการรับน้ำหนักตาม Truckscale (เงื่อนไขการคำนวณรับ/ส่งสินค้า ตามน้ำหนักจาก Odoo หรือใช้น้ำหนักจาก Truckscale)")

    # ux field
    is_default_code_from_sequence = fields.Boolean(string='Code from sequence',readonly=True)
    gross_weight = fields.Float(string='Gross Weight', compute='_compute_gross_weight', digits='Stock Weight', inverse='_set_gross_weight', store=True)

    # Cost calculation fields
    update_standard_price = fields.Boolean(
        string='Cost Updated',
        compute='_compute_update_standard_price',
        inverse='_set_update_standard_price',
        help="""Is set if standard_price (Cost) was update by Manufacturing process 
        and will not re-write by Compute Price from BoM.""")
    basic_cost = fields.Float(
        string='Basic Cost',
        compute='_compute_basic_cost',
        inverse='_set_basic_cost',
        digits='Product Price',
        groups="base.group_user",
        help="Basic Cost for use as base calculate in Manufacturing Orders.")


    @api.depends('product_variant_ids', 'product_variant_ids.weight')
    def _compute_gross_weight(self):
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.gross_weight = template.product_variant_ids.gross_weight
        for template in (self - unique_variants):
            template.gross_weight = 0.0

    def _set_gross_weight(self):
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.product_variant_ids.gross_weight = template.gross_weight

    @api.depends('product_variant_ids', 'product_variant_ids.update_standard_price')
    def _compute_update_standard_price(self):
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.update_standard_price = template.product_variant_ids.update_standard_price
        for template in (self - unique_variants):
            template.update_standard_price = False

    def _set_update_standard_price(self):
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.product_variant_ids.update_standard_price = template.update_standard_price

    @api.depends('product_variant_ids', 'product_variant_ids.basic_cost')
    def _compute_basic_cost(self):
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.basic_cost = template.product_variant_ids.basic_cost
        for template in (self - unique_variants):
            template.basic_cost = 0.0

    def _set_basic_cost(self):
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.product_variant_ids.basic_cost = template.basic_cost


    @api.model
    def create(self, vals):
        if vals.get('default_code'):
            return super().create(vals)
        categ_id = self.env['product.category'].browse(vals.get('categ_id'))
        vals.update(default_code=categ_id._get_sequence(), is_default_code_from_sequence=True)
        return super().create(vals)
