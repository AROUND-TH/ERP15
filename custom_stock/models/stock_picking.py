# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'


    # @Override method button_validate
    def button_validate(self):
        res = super(StockPicking, self).button_validate()

        for picking in self:
            for line in picking.move_line_ids:
                product = line.product_id

                if product and product.custom_fleet_ok == True:
                    if product.qty_available > 0:
                        pass
                        # @Remark for manual flag "Can be Sold"
                        # product.sale_ok = True
                    else:
                        product.sale_ok = False

        return res

