# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class WizardScheduleDelivery(models.TransientModel):
    _name = 'schedule.delivery'
    _description = 'Schedule Delivery'

    sale_line_id = fields.Many2one('sale.order.line', string='Sale Order Line')
    total_qty = fields.Float(string='Sale Line Total Quantity', related='sale_line_id.product_uom_qty')
    schedule_delivery_ids = fields.One2many('schedule.delivery.line', 'delivery_line_id')
    product_id = fields.Many2one('product.product', string='Product', related='sale_line_id.product_id')

    @api.model
    def default_get(self, fields):
        active_ids = self._context.get('active_ids')
        res = super(WizardScheduleDelivery, self).default_get(fields)
        sale_order = self.env['sale.order.line'].browse(active_ids)
        sale_lines = []
        for line in sale_order.delivery_line_ids:
            move = (0, 0, {
                'date': line.date,
                'qty': line.qty,
            })
            sale_lines.append(move)
            res.update({
                'schedule_delivery_ids': sale_lines,
            })
        return res

    def update_values(self):
        if not self.schedule_delivery_ids:
            raise ValidationError(_('''Please enter some Delivery Details'''))
        if any(line.qty <= 0 for line in self.schedule_delivery_ids):
            raise ValidationError(_('''All lines quantity must be positive, please do not enter Zero'''))
        line_total = sum(line.qty for line in self.schedule_delivery_ids)
        if line_total > self.total_qty:
            raise ValidationError(_('''Sale Line Total Quantity is %s\nYou are trying to enter %s\nPlease enter total %s quantity or less than it''') %
                                  (self.total_qty, line_total, self.total_qty))
        active_ids = self._context.get('active_ids')
        sale_ids = self.env['sale.order.line'].browse(active_ids)
        sale_ids.delivery_line_ids.unlink()
        for delivery in self.schedule_delivery_ids:
            val_lst = []
            vals = {
                'date': delivery.date,
                'qty': delivery.qty,
            }
            val_lst.append((0, 0, vals))
            sale_ids.delivery_line_ids = val_lst


class WizardScheduleDeliveryLine(models.TransientModel):
    _name = 'schedule.delivery.line'
    _description = 'Schedule Delivery Line'

    delivery_line_id = fields.Many2one('schedule.delivery', ondelete='cascade')
    date = fields.Datetime(string='Date', required=True)
    qty = fields.Float(string='Quantity')
    schedule_delivery_ids = fields.One2many('schedule.delivery.line', 'delivery_line_id')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: