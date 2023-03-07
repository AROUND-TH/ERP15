# -*- coding: utf-8 -*-

from odoo import _, models, fields, api
from datetime import datetime, timedelta
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class CreditMessageError(models.Model):
    _name = 'credit.message.error'
    _description = "Currency"

    name = fields.Char(
        string='Name',
        required=True,
    )
    user_id = fields.Many2one('res.users', 'User', required=True, tracking=True, readonly=True, default=lambda self: self.env.user)
    message_th = fields.Text(string='Message TH', required=True)
    message_en = fields.Text(string='Message EN', required=True)
    error_type = fields.Selection(
        selection=[
            ('customer','Receivable Amount of Customer'),
            ('days','Due Amount Till Days'),
        ],
        string='Message Error of',
        default='days'
    )
    
    @api.model
    def create(self, values):
        message_ids = self.env['credit.message.error'].search([('error_type', '=', values.get('error_type'))])
        
        if len(message_ids) == 1:
            raise UserError(_("You can't create data greater than 1 record for this type."))

        return super(CreditMessageError, self).create(values)