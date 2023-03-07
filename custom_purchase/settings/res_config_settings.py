# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pr_approval_procedure = fields.Boolean('Approve all PR by Approval Procedure process.', help="All PR must to pass the approve by Approval Procedure process.")
    po_approval_procedure = fields.Boolean('Approve all PO by Approval Procedure process.', help="All PO must to pass the approve by Approval Procedure process.")


    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ir_config = self.env['ir.config_parameter'].sudo()

        res.update(
            pr_approval_procedure=ir_config.get_param('purchase.pr_approval_procedure'),
            po_approval_procedure=ir_config.get_param('purchase.po_approval_procedure')
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ir_config = self.env['ir.config_parameter'].sudo()
        ir_config.set_param("purchase.pr_approval_procedure", self.pr_approval_procedure)
        ir_config.set_param("purchase.po_approval_procedure", self.po_approval_procedure)

