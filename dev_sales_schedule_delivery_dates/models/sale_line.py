# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################

from odoo import api, fields, models, _
from datetime import datetime

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _prepare_procurement_group_vals(self):
        res = super(SaleOrderLine, self)._prepare_procurement_group_vals()
        res.update({'delivery_date': self.new_delivery_date})
        return res

    def _prepare_procurement_values(self, group_id=False):
        res = super(SaleOrderLine, self)._prepare_procurement_values(group_id=group_id)
        if self.new_delivery_date:
            res.update({'date_planned': self.new_delivery_date,
                        'date_deadline': self.new_delivery_date})
        return res

    def _action_launch_stock_rule(self, previous_product_uom_qty=False):
        """
        Launch procurement group run method with required/custom fields genrated by a
        sale order line. procurement group will launch '_run_pull', '_run_buy' or '_run_manufacture'
        depending on the sale order line product rule.
        """
        procurements = []
        for sale_line in self:
            line = sale_line
            if sale_line.delivery_line_ids:
                for delivery_line in sale_line.delivery_line_ids:
                    line.new_delivery_date = delivery_line.date
                    line = line.with_company(line.company_id)
                    if line.state != 'sale' or not line.product_id.type in ('consu','product'):
                        continue
                    qty = delivery_line.qty
                    group_id = self.env['procurement.group'].search([('sale_id', '=', line.order_id.id),
                                                                     ('delivery_date', '=', line.new_delivery_date)])
                    if not group_id:
                        group_id = self.env['procurement.group'].create(line._prepare_procurement_group_vals())
                    else:
                        # In case the procurement group is already created and the order was
                        # cancelled, we need to update certain values of the group.
                        updated_vals = {}
                        if group_id.partner_id != line.order_id.partner_shipping_id:
                            updated_vals.update({'partner_id': line.order_id.partner_shipping_id.id})
                        if group_id.move_type != line.order_id.picking_policy:
                            updated_vals.update({'move_type': line.order_id.picking_policy})
                        if updated_vals:
                            group_id.write(updated_vals)
                    values = line._prepare_procurement_values(group_id=group_id)
                    line_uom = line.product_uom
                    quant_uom = line.product_id.uom_id
                    product_qty, procurement_uom = line_uom._adjust_uom_quantities(qty, quant_uom)
                    procurements.append(self.env['procurement.group'].Procurement(
                        line.product_id, product_qty, procurement_uom,
                        line.order_id.partner_shipping_id.property_stock_customer,
                        line.name, line.order_id.name, line.order_id.company_id, values))
                # we need to take, remaining qty which user has not entered
                if line.remaining_schedule_date_qty > 0:
                    line.new_delivery_date = line.order_id and line.order_id.commitment_date or line.order_id.expected_date
                    line = line.with_company(line.company_id)
                    if line.state != 'sale' or not line.product_id.type in ('consu', 'product'):
                        continue
                    qty = line.remaining_schedule_date_qty
                    group_id = self.env['procurement.group'].search([('sale_id', '=', line.order_id.id),
                                                                     ('delivery_date', '=', line.new_delivery_date)])
                    if not group_id:
                        group_id = self.env['procurement.group'].create(line._prepare_procurement_group_vals())
                    else:
                        # In case the procurement group is already created and the order was
                        # cancelled, we need to update certain values of the group.
                        updated_vals = {}
                        if group_id.partner_id != line.order_id.partner_shipping_id:
                            updated_vals.update({'partner_id': line.order_id.partner_shipping_id.id})
                        if group_id.move_type != line.order_id.picking_policy:
                            updated_vals.update({'move_type': line.order_id.picking_policy})
                        if updated_vals:
                            group_id.write(updated_vals)
                    values = line._prepare_procurement_values(group_id=group_id)
                    line_uom = line.product_uom
                    quant_uom = line.product_id.uom_id
                    product_qty, procurement_uom = line_uom._adjust_uom_quantities(qty, quant_uom)
                    procurements.append(self.env['procurement.group'].Procurement(
                        line.product_id, product_qty, procurement_uom,
                        line.order_id.partner_shipping_id.property_stock_customer,
                        line.name, line.order_id.name, line.order_id.company_id, values))

            else:
                line.new_delivery_date = line.order_id and line.order_id.commitment_date or line.order_id.expected_date
                line = line.with_company(line.company_id)
                if line.state != 'sale' or not line.product_id.type in ('consu', 'product'):
                    continue
                qty = line._get_qty_procurement(previous_product_uom_qty)
                group_id = self.env['procurement.group'].search([('sale_id', '=', line.order_id.id),
                                                                 ('delivery_date', '=', line.new_delivery_date)])
                if not group_id:
                    group_id = self.env['procurement.group'].create(line._prepare_procurement_group_vals())
                else:
                    # In case the procurement group is already created and the order was
                    # cancelled, we need to update certain values of the group.
                    updated_vals = {}
                    if group_id.partner_id != line.order_id.partner_shipping_id:
                        updated_vals.update({'partner_id': line.order_id.partner_shipping_id.id})
                    if group_id.move_type != line.order_id.picking_policy:
                        updated_vals.update({'move_type': line.order_id.picking_policy})
                    if updated_vals:
                        group_id.write(updated_vals)

                values = line._prepare_procurement_values(group_id=group_id)
                product_qty = line.product_uom_qty - qty
                line_uom = line.product_uom
                quant_uom = line.product_id.uom_id
                product_qty, procurement_uom = line_uom._adjust_uom_quantities(product_qty, quant_uom)
                procurements.append(self.env['procurement.group'].Procurement(
                    line.product_id, product_qty, procurement_uom,
                    line.order_id.partner_shipping_id.property_stock_customer,
                    line.name, line.order_id.name, line.order_id.company_id, values))
        if procurements:
            self.env['procurement.group'].run(procurements)
        return True

    def _compute_remaining_schedule_date_qty(self):
        for rec in self:
            remaining = 0
            entered_qty = 0
            if rec.delivery_line_ids:
                entered_qty = sum(line.qty for line in rec.delivery_line_ids)
            if entered_qty > 0:
                remaining = rec.product_uom_qty - entered_qty
            rec.remaining_schedule_date_qty = remaining

    delivery_line_ids = fields.One2many('sale.delivery.line', 'sale_line_id')
    new_delivery_date = fields.Datetime(string='New Delivery Date')
    remaining_schedule_date_qty = fields.Float(string='Remaining Quantity', compute='_compute_remaining_schedule_date_qty')

class SaleDeliveryLine(models.Model):
    _name = 'sale.delivery.line'
    _description = 'SaleDeliveryLine'

    sale_line_id = fields.Many2one('sale.order.line', string='Sale Order Line', ondelete='cascade')
    date = fields.Datetime(string='Date')
    qty = fields.Float(string='Quantity')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: