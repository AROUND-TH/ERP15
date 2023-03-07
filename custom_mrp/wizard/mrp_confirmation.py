from odoo import models,fields,api
from odoo.tools import float_round

class MRPConfirmation(models.TransientModel):
    _inherit = "mrp.confirmation"

    is_middleware_data = fields.Boolean("Middleware Data",default=False)

    @api.onchange('workorder_id', 'qty_output_wo')
    def onchange_workorder_id_qty_output_wo(self):
        quantity = 0.0
        prod_quantity = 0.0
        cycle_number = 0.0
        prod_cycle_number = 0.0
        duration_expected_working = 0.0
        for record in self:
            if record.workorder_id and not record.is_middleware_data:
                prod_quantity = record.production_id.product_uom_qty
                prod_cycle_number = float_round(prod_quantity / record.workorder_id.workcenter_id.capacity, precision_digits=0, rounding_method='UP')
                duration_expected_working = (record.workorder_id.duration_expected - record.workorder_id.workcenter_id.time_start - record.workorder_id.workcenter_id.time_stop) * record.workorder_id.workcenter_id.time_efficiency / (100.0 * prod_cycle_number)
                if duration_expected_working < 0.0:
                    duration_expected_working = 0.0
                quantity = record.product_uom_id._compute_quantity(record.qty_output_wo, record.product_id.product_tmpl_id.uom_id)
                cycle_number = float_round(quantity / record.workorder_id.workcenter_id.capacity, precision_digits=0, rounding_method='UP')
                record.working_duration = duration_expected_working * cycle_number * 100.0 / record.workorder_id.workcenter_id.time_efficiency or 0.0
                record.setup_duration = record.workorder_id.workcenter_id.time_start or 0.0
                record.teardown_duration = record.workorder_id.workcenter_id.time_stop or 0.0