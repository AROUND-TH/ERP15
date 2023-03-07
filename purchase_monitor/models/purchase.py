# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    open_to_receive = fields.Boolean("Open Receipts", compute="_compute_open_to_receive", store=True, compute_sudo=True)


    @api.depends('order_line.qty_to_receive')
    def _compute_open_to_receive(self):
        for order in self:
            order.open_to_receive = True if sum(order.mapped("order_line.qty_to_receive")) > 0.0 else False
        return True


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    price_unit = fields.Float(group_operator=False)
    amount_received = fields.Float("Received Amount", compute="_compute_received", compute_sudo=True)
    amount_invoiced = fields.Float("Billed Amount", compute="_compute_received", compute_sudo=True)
    qty_to_receive = fields.Float("Qty to be Received", compute="_compute_to_receive", digits="Product Unit of Measure", store=True, compute_sudo=True)
    qty_to_invoice = fields.Float("Qty to be Invoiced", compute="_compute_to_receive", digits="Product Unit of Measure", store=True, compute_sudo=True)
    amount_to_receive = fields.Float("Amount to be Received", compute="_compute_to_receive", compute_sudo=True)
    amount_to_invoice = fields.Float("Amount to be Invoiced", compute="_compute_to_receive", compute_sudo=True)
    purchase_method = fields.Selection(related='product_id.purchase_method')
    user_id = fields.Many2one('res.users', 'Buyer', related='order_id.user_id')
    origin = fields.Char('Source Document', related='order_id.origin')
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', related='order_id.picking_type_id.warehouse_id')


    @api.depends('price_unit','qty_received','qty_invoiced')
    def _compute_received(self):
        for record in self:
            record.amount_received  = record.price_unit * record.qty_received
            record.amount_invoiced = record.price_unit * record.qty_invoiced
        return True


    @api.depends('move_ids','move_ids.state','price_unit','qty_received','product_qty','qty_invoiced','purchase_method')
    def _compute_to_receive(self):
        for record in self:
            qty = 0
            for move in record.move_ids.filtered(lambda m: m.state not in ("cancel", "done")):
                qty += move.product_uom_qty
            record.qty_to_receive = qty
            record.amount_to_receive = record.price_unit * record.qty_to_receive
            if record.purchase_method == 'purchase':
                record.qty_to_invoice = record.product_qty - record.qty_invoiced
                record.amount_to_invoice = record.price_unit * record.qty_to_invoice
            else:
               record.qty_to_invoice = record.qty_received - record.qty_invoiced
               record.amount_to_invoice = record.price_unit * record.qty_to_invoice
        return True


class PurchaseOrderLineHistory(models.TransientModel):
    _name = 'purchase.order.line.history'
    _description = "Purchase Order Line History"


    purchase_line_id = fields.Many2one('purchase.order.line', string="Purchase Order Line", readonly=True)
    purchase_id = fields.Many2one('purchase.order', string="Purchase Order", readonly=True)
    invoice_lines = fields.Many2many('account.move.line', string="Invoice Lines", readonly=True, compute='get_records')
    move_ids = fields.Many2many('stock.move', string="Stock Moves", readonly=True, compute='get_records')



    def default_get(self, fields):
        default = super().default_get(fields)
        active_id = self.env.context.get('active_id', False)
        if active_id:
            default['purchase_line_id'] = active_id
        return default

    @api.depends('purchase_line_id')
    def get_records(self):
        self.ensure_one()
        self.purchase_id = self.purchase_line_id.order_id.id
        self.invoice_lines = self.purchase_line_id.invoice_lines
        self.move_ids = self.purchase_line_id.move_ids
        return True
