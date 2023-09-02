from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    car_order_commission_product_category_id = fields.Many2one('product.category',
                                                               string="Product Category for Commission",
                                                               required=True,
                                                               config_parameter="car_order_commission_product_category")
    car_order_vendor_group_car = fields.Many2one('vendor.group',
                                                 string="Vendor Group",
                                                 required=True,
                                                 config_parameter="car_order_vendor_group_car")
