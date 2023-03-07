# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class SaleAuthentication(models.Model):
    _name = "sale.authentication"
    _description = "Authentication"
    _order = 'id desc'

    name = fields.Char('Reference', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    positions_id = fields.Many2one('hr.job', string='Positions', required=True)
    user_approve_id = fields.Many2one(
        'hr.employee', 
        string='Approver', 
        index=True, 
        required=True,
        domain="[('job_id', '=', positions_id)]",    
    )

    @api.onchange("positions_id")
    def _change_position_for_pr(self):
        self.user_approve_id = False


    @api.model
    def create(self, values):
        authentication_ids = self.env['sale.authentication'].search([])
        if len(authentication_ids) == 1:
            raise UserError(_("You can't create data greater than 1 record."))

        if values.get('name', _('New')) == _('New'):
            user_approve_id = self.env['hr.employee'].browse(values['user_approve_id'])
            positions_id = self.env['hr.job'].browse(values['positions_id'])
            values['name'] = str(positions_id.name) + ' / ' + str(user_approve_id.name)

        return super(SaleAuthentication, self).create(values)
        