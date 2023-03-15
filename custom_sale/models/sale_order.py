# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"


    # @Override method action_confirm
    def action_confirm(self):
        result = super(SaleOrder, self).action_confirm()
        if result:
            for order in self:
                for line in order.order_line:
                    product = line.product_id

                    if product and product.custom_fleet_ok == True:
                        product.sale_ok = False

        return result

