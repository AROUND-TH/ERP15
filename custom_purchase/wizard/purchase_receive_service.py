
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseReceiveServiceLine(models.TransientModel):
    _name = "purchase.receive.service.line"
    _rec_name = 'product_id'
    _description = 'Return Picking Line'

    line_id = fields.Many2one('purchase.order.line', "Move")
    product_id = fields.Many2one('product.product', string="Product", required=True)
    quantity = fields.Float("Quantity", digits='Product Unit of Measure', required=True)
    qty_received = fields.Float("Received", digits='Product Unit of Measure', required=True)
    receive = fields.Float("Receive", digits='Product Unit of Measure', required=True, default=0)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', related='product_id.uom_id')
    wizard_id = fields.Many2one('purchase.receive.service', string="Wizard")

    @api.constrains('receive')
    def _validate(self):
        for rec in self:
            if rec.receive < 0:
                raise ValidationError(_('Receive must more then zero.'))
            if rec.receive + rec.qty_received > rec.quantity:
                raise ValidationError(_('Can\'t receive more then Quantity.'))


class PurchaseReceiveService(models.TransientModel):
    _name = "purchase.receive.service"
    _description = 'Return Picking'

    @api.model
    def default_get(self, fields):
        res = super(PurchaseReceiveService, self).default_get(fields)
        if self.env.context.get('active_id') and self.env.context.get('active_model') == 'purchase.order':
            if len(self.env.context.get('active_ids', list())) > 1:
                raise UserError(_("You may only receive one purchase at a time."))
            purchase_id = self.env['purchase.order'].browse(self.env.context.get('active_id'))
            if purchase_id.exists():
                res.update({'purchase_id': purchase_id.id})
        return res

    purchase_id = fields.Many2one('purchase.order')
    receive_line = fields.One2many('purchase.receive.service.line', 'wizard_id', 'Services')

    def action_receive(self):
        for rec in self:
            for receive_id in rec.receive_line:
                if receive_id.receive == 0:
                    continue
                receive_id.line_id.qty_received += receive_id.receive
            rec.purchase_id.confirm_reminder_mail()

    @api.onchange('purchase_id')
    def _onchange_picking_id(self):
        receive_line = list()
        if self.purchase_id and self.purchase_id.state != 'done':
            raise UserError(_("You may only return Locked purchase."))
        for line_id in self.purchase_id.order_line:
            if line_id.product_id.type != "service":
                continue
            if line_id.product_qty == line_id.qty_received:
                continue
            receive_line.append((0, 0, {
                'product_id': line_id.product_id.id,
                'quantity': line_id.product_qty,
                'qty_received': line_id.qty_received,
                'uom_id': line_id.product_uom.id,
                'line_id': line_id.id,
            }))
        self.receive_line = receive_line
