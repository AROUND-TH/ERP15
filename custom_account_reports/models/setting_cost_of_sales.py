# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SettingCostOfSales(models.Model):
    _name = "setting.cost.sales"
    _description = "Setting Cost Of Sales Report"
    _order = 'id desc'

    name = fields.Char('Name', required=True, copy=False, index=True)
    group_account_inventories_start_ids = fields.Many2many('account.account', 'account_account_inventories_start', 'account_id', 'set_cost_sale_id', string='กลุ่มบัญชีสินค้าคงเหลือต้นงวด')
    group_account_finished_goods_ids = fields.Many2many('account.account', 'account_account_finished_goods', 'account_id', 'set_cost_sale_id', string='กลุ่มบัญชีสินค้าสำเร็จรูป')
    group_account_inventories_end_ids = fields.Many2many('account.account', 'account_account_inventories_end', 'account_id', 'set_cost_sale_id', string='กลุ่มบัญชีสินค้าคงเหลือต้นปลายงวด')

    @api.model
    def create(self, values):
        production_ids = self.env['setting.cost.sales'].search([])
        if len(production_ids) == 1:
            raise UserError(_("You can't create data greater than 1 record."))

        return super(SettingCostOfSales, self).create(values)
