# -*- coding: utf-8 -*-


from odoo import api, fields, models, _


class MrpPlanningVolume(models.Model):
    _name = "mrp.planning.volume"
    _description = "MRP Planning Volume"
    _order = "sequence"

    sequence = fields.Integer('Planning Sequence', default=10, required=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', required=True)
    company_id = fields.Many2one("res.company", "Company", related="warehouse_id.company_id", store=True, readonly=True)


    _sql_constraints = [("sequence_uniq", "unique(sequence)", "The planning sequence must be unique.",)]

    #@api.constrains("sequence", "warehouse_id")
    #def _check_archive(self):
    #    for record in self:
    #        warehouses = self.env["mrp.planning.volume"].search([
    #            ("warehouse_id", "=", record.warehouse_id.id),
    #            ("sequence", "=", record.sequence),
    #            ])
    #        if len(warehouses) > 1:
    #                raise UserError(_("The planning sequence must be unique."))
    #   return True

