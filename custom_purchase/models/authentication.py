from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PurchaseAuthentication(models.Model):
    _name = "purchase.authentication"
    _description = "Authentication"
    _order = 'id desc'

    name = fields.Char('Reference', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    positions_pr_id = fields.Many2one('hr.job', string='Positions for PR', required=True)
    positions_po_id = fields.Many2one('hr.job', string='Positions for PO', required=True)
    user_pr_id = fields.Many2one(
        'hr.employee',
        string='MD for Approve PR',
        index=True,
        required=True,
        domain="[('job_id', '=', positions_pr_id)]",
    )
    user_po_id = fields.Many2one(
        'hr.employee',
        string='MD for Approve PO',
        index=True,
        required=True,
        domain="[('job_id', '=', positions_po_id)]",
    )

    @api.onchange("positions_pr_id")
    def _change_position_for_pr(self):
        self.user_pr_id = False

    @api.onchange("positions_po_id")
    def _change_position_for_po(self):
        self.user_po_id = False

    @api.model
    def create(self, values):
        authentication_ids = self.env['purchase.authentication'].search([])
        if len(authentication_ids) == 1:
            raise UserError(_("You can't create data greater than 1 record."))

        if values.get('name', _('New')) == _('New'):
            user_pr_id = self.env['hr.employee'].browse(values['user_pr_id'])
            user_po_id = self.env['hr.employee'].browse(values['user_po_id'])
            values['name'] = str(user_pr_id.name) + ' / ' + str(user_po_id.name)

        return super(PurchaseAuthentication, self).create(values)
