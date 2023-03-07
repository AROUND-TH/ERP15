# -*- coding: utf-8 -*-

from odoo import models, fields, _
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    custom_requisition_id = fields.Many2one(
        'material.purchase.requisition',
        string='Purchase Requisition',
        readonly=True,
        copy=True
    )

    def action_confirm(self):
        res = super().action_confirm()
        for rec in self:
            if rec.custom_requisition_id:
                rec.must_validate = True
        return res

    def button_validate(self):
        for rec in self:
            if rec.picking_type_id == rec.picking_type_id.warehouse_id.int_type_id and rec.custom_requisition_id and rec.custom_requisition_id.create_uid != rec.env.user:
                raise ValidationError(_('Only creator of requisitions can Validate.'))
        return super().button_validate()


class StockMove(models.Model):
    _inherit = 'stock.move'

    custom_requisition_line_id = fields.Many2one(
        'material.purchase.requisition.line',
        string='Requisitions Line',
        copy=True
    )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
