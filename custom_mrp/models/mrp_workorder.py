from odoo import models,fields,api
import logging

_logger = logging.getLogger(__name__)

class MRP_WorkOrder(models.Model):
    _inherit = 'mrp.workorder'

    def write(self, values):
        res = super(MRP_WorkOrder, self).write(values)
        _logger.info(values)
        for rec in self:
            if values.get("date_planned_start") and values.get("date_planned_finish"):
                _logger.info(values.get("date_planned_start"))
                _logger.info(values.get("date_planned_finish"))
        return res