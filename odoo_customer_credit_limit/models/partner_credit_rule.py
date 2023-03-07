# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, timedelta
import logging
_logger = logging.getLogger(__name__)

class PartnerCreditRule(models.Model):
    _name = 'partner.credit.rule'
    _description = "Partner Credit Rule"
    
    name = fields.Char(
        string='Name',
        required=True,
    )
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, default=lambda self: self.env.company)
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True, change_default=True, index=True, tracking=1,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )
    categ_ids = fields.Many2many('product.category', string='Product Categories')
    product_tmpl_ids = fields.Many2many('product.template', string='Products')
    credit_limit = fields.Float('Credit Limits', required=True)
    credit_days = fields.Integer(string='Days')
    code = fields.Char(string='Code')
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        readonly=True,
        default=lambda self: self.company_id.currency_id
    )
    history_line_ids = fields.One2many(
        'history.credit.rule', 
        'credit_rule_id',
        string='History Credit Rule',
    )
    
    credit_type = fields.Selection(
        selection=[
            ('customer','Receivable Amount of Customer'),
            ('days','Due Amount Till Days'),
        ],
        string='Credit Limit Formula',
        default='days'
    )

    @api.model
    def create(self, values):
        res = super(PartnerCreditRule, self).create(values)
        res.history_line_ids = ([(0, 0, {
            'credit_rule_id': res.id,
            'history_type': 'create',
            'user_id': self.env.user.id,
            'date': fields.Datetime.now(),
            'credit_limit': str(res.credit_limit if res.credit_limit else ''),
            'credit_days': str(res.credit_days if res.credit_days else ''),
        })])

        return res

    def write(self, values):
        is_update_history = False
        credit_limit = ''
        credit_days = ''

        if values.get('credit_limit'):
            credit_limit = values.get('credit_limit')
            is_update_history =True

        if values.get('credit_days'):
            credit_days = values.get('credit_days')
            is_update_history =True

        if is_update_history:
            self.history_line_ids = ([(0, 0, {
                'credit_rule_id': self.id,
                'history_type': 'update',
                'user_id': self.env.user.id,
                'date': fields.Datetime.now(),
                'credit_limit': credit_limit,
                'credit_days': credit_days,
            })])

        return super(PartnerCreditRule, self).write(values)


class HistoryCreditRule(models.Model):
    _name = 'history.credit.rule'
    _description = "History Credit Rule"
    _order = 'id desc'

    credit_rule_id = fields.Many2one('partner.credit.rule', 
        string='Credit Limit Rule',
        index=True,
    )
    user_id = fields.Many2one('res.users', string='User')
    date = fields.Datetime(
        string='Date',
        default=fields.Datetime.now,
    )
    history_type = fields.Selection(
        selection=[
            ('create','Create'),
            ('update','Update'),
        ],
        string='Type',
        default='create'
    )
    credit_limit = fields.Char(
        'Credit Limits',
    )
    credit_days = fields.Char(
        string='Days',
    )