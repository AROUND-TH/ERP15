# -*- coding: utf-8 -*-

from odoo import api, models, _
from odoo.exceptions import UserError


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = 'product.product'
    _description = 'Product'


    # @Override odoo core method _set_price_from_bom
    def _set_price_from_bom(self, boms_to_recompute=False):
        self.ensure_one()

        bom = self.env['mrp.bom']._bom_find(self)[self]
        if bom:
            # self.standard_price = self._compute_bom_price(bom, boms_to_recompute=boms_to_recompute)
            price = self._compute_bom_price(bom, boms_to_recompute=boms_to_recompute)
            if not self.update_standard_price:
                self.standard_price = price
            self.basic_cost = price
        else:
            bom = self.env['mrp.bom'].search([('byproduct_ids.product_id', '=', self.id)], order='sequence, product_id, id', limit=1)
            if bom:
                price = self._compute_bom_price(bom, boms_to_recompute=boms_to_recompute, byproduct_bom=True)
                if price:
                    if not self.update_standard_price:
                        self.standard_price = price
                    self.basic_cost = price


    def _compute_bom_price(self, bom, boms_to_recompute=False, byproduct_bom=False):
        self.ensure_one()
        if not bom:
            return 0
        # esclusione delle by-product boms
        if byproduct_bom:
            return 0
        if not boms_to_recompute:
            boms_to_recompute = []
        #total = 0
        total = costvar = costfixed = byproductamount = 0
        # operations
        for operation in bom.operation_ids:
            if operation._skip_operation_line(self):
                continue
            #duration_expected = (
            #    opt.workcenter_id.time_start +
            #    opt.workcenter_id.time_stop +
            #    opt.time_cycle)
            #total += (duration_expected / 60) * opt.workcenter_id.costs_hour
            costvar += (operation.time_cycle/60) * operation.workcenter_id.costs_hour
            costfixed += (operation.workcenter_id.time_stop + operation.workcenter_id.time_start) * operation.workcenter_id.costs_hour_fixed/60
        total += costvar + costfixed
        # components
        for line in bom.bom_line_ids:
            if line._skip_bom_line(self):
                continue
            # Compute recursive if line has `child_line_ids`
            if line.child_bom_id and line.child_bom_id in boms_to_recompute:
                child_total = line.product_id._compute_bom_price(line.child_bom_id, boms_to_recompute=boms_to_recompute)
                total += line.product_id.uom_id._compute_price(child_total, line.product_uom_id) * line.product_qty
            else:
                total += line.product_id.uom_id._compute_price(line.product_id.standard_price, line.product_uom_id) * line.product_qty
        # by products
        for byproduct_id in bom.byproduct_ids:
            byproductamount += byproduct_id.product_id.standard_price * byproduct_id.product_qty
        total -= byproductamount
        return bom.product_uom_id._compute_price(total / bom.product_qty, self.uom_id)

