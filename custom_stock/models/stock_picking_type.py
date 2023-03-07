from odoo import models, fields, api


class PickingType(models.Model):
    _inherit = 'stock.picking.type'

    interface_truckscale_data = fields.Boolean(
        'Use Interface Truckscale Data',
        default=False,
        help="If this is checked, you can Interface Truckscale Data from API."
    )
    set_done_by_weight = fields.Boolean(
        'Set Done Quantity by Weight',
        default=False,
        help="If this is checked, Done Quantity will update by Netweight from API. (Depend on Product Master setting)"
    )
    show_truckscale_data = fields.Boolean(
        'Show Truckscale Data',
        default=False,
        help="If this is checked, The Truckscale Data will show up. (Depend on Interface Data and Business Logic)"
    )

    @api.onchange('interface_truckscale_data')
    def _onchange_interface_truckscale_data(self):
        self.set_done_by_weight = self.interface_truckscale_data
