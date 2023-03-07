from odoo import models, fields, _

RETURN_REASON = [
    ('not_quality', 'สินค้าไม่ได้คุณภาพ'),
    ('damaged', 'สินค้าเสียหาย'),
    ('detail_not_match', 'สินค้าไม่ตรงตามรายละเอียด'),
    ('incomplete', 'สินค้าไม่ครบถ้วน'),
    ('expired', 'สินค้าหมดอายุ'),
]


class ReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking"

    reason = fields.Selection(RETURN_REASON, required=True)
    remark = fields.Text(string="Remark")

    def _prepare_picking_default_values(self):
        return {
            'move_lines': [],
            'picking_type_id': self.picking_id.picking_type_id.return_picking_type_id.id or self.picking_id.picking_type_id.id,
            'state': 'draft',
            'origin': _("Return of %s") % self.picking_id.name,
            'location_id': self.picking_id.location_dest_id.id,
            'location_dest_id': self.location_id.id,
            'show_return_info': True,
            'return_reason': self.reason,
            'return_remark': self.remark
        }
