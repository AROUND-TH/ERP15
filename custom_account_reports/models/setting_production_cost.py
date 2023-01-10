# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SettingProductionCost(models.Model):
    _name = "setting.production.cost"
    _description = "Setting Production Cost Report"
    _order = 'id desc'

    name = fields.Char('Name', required=True, copy=False, index=True)
    group_account_raw_mate_ids = fields.Many2many('account.account', 'account_account_raw_mate', 'account_id', 'set_production_cost_id', string='กลุ่มบัญชีวัตถุดิบ')
    group_account_direct_labor_ids = fields.Many2many('account.account', 'account_account_direct_labor', 'account_id', 'set_production_cost_id', string='กลุ่มบัญชีค่าแรงงานทางตรง')
    group_account_production_ids = fields.Many2many('account.account', 'account_account_production', 'account_id', 'set_production_cost_id', string='กลุ่มบัญชีค่าใช้จ่ายในการผลิต')
    group_account_start_progress_ids = fields.Many2many('account.account', 'account_account_start_progress', 'account_id', 'set_production_cost_id', string='กลุ่มบัญชีงานระหว่างทำต้นงวด')
    group_account_end_progress_ids = fields.Many2many('account.account', 'account_account_end_progress', 'account_id', 'set_production_cost_id', string='กลุ่มบัญชีงานระหว่างทำปลายงวด')


    @api.model
    def create(self, values):
        production_ids = self.env['setting.production.cost'].search([])
        if len(production_ids) == 1:
            raise UserError(_("You can't create data greater than 1 record."))

        return super(SettingProductionCost, self).create(values)
