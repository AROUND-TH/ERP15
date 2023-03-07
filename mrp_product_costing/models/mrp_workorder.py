# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
from datetime import date


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'


    direct_cost = fields.Boolean('Direct Cost', copy=False, default=False)


    def _create_or_update_analytic_entry(self):
        return True

    def button_finish(self):
        res = super().button_finish()
        for record in self:
            if record.state == 'done' and not record.direct_cost:
                record._direct_cost_postings()
                record.direct_cost = True
        return res

    # production direct cost posting
    def _direct_cost_postings(self):
        total_working_duration = 0.0
        total_fixed_duration = 0.0
        amount_variable = 0.0
        amount_fixed = 0.0
        final_date = False
        for record in self:
            desc_wo = record.production_id.name + '-' + record.workcenter_id.name + '-' + record.name
            last_time = self.env['mrp.workcenter.productivity'].search([('workorder_id', '=', record.id),('date_end', '!=', False)], order=	"date_end desc", limit=1)
            if last_time:
                final_date = last_time.date_end.date()
            else:
                final_date = date.today()
            analytic_account = record.production_id.analytic_account_id.id or record.workcenter_id.analytic_account_id.id
            for time in record.time_ids:
                if time.overall_duration:
                    total_working_duration += time.working_duration
                    total_fixed_duration += time.setup_duration + time.teardown_duration
                else:
                    total_working_duration += time.duration
            amount_variable = round((total_working_duration * record.workcenter_id.costs_hour)/ 60, 2)
            amount_fixed = round((total_fixed_duration * record.workcenter_id.costs_hour_fixed)/ 60, 2)
            if amount_variable or amount_fixed:
                if record.workcenter_id.wc_type == "H":
                    variable_account_id = record.production_id.company_id.labour_cost_account_id
                    fixed_account_id = record.production_id.company_id.labour_fixed_cost_account_id
                else:
                    variable_account_id = record.production_id.company_id.machine_run_cost_account_id
                    fixed_account_id = record.production_id.company_id.machine_run_fixed_cost_account_id
                id_created_header = self.env['account.move'].create({
                    'journal_id' : record.production_id.company_id.manufacturing_journal_id.id,
                    'date': final_date,
                    'ref' : desc_wo,
                    'company_id': record.workcenter_id.company_id.id,
                    'manufacture_order_id': record.production_id.id,
                })
                if amount_variable:
                    id_credit_item_variable = self.env['account.move.line'].with_context(check_move_validity=False).create({
                        'move_id' : id_created_header.id,
                        'account_id': variable_account_id.id,
                        'product_id': record.production_id.product_id.id,
                        'name' : " ".join(("Direct Variable Costs", record.name)),
                        'quantity': record.qty_output_wo,
                        'product_uom_id': record.production_id.product_uom_id.id,
                        'credit': amount_variable,
                        'debit': 0.0,
                        #'manufacture_order_id': record.production_id.id,
                    })
                    id_debit_item_variable = self.env['account.move.line'].with_context(check_move_validity=False).create({
                        'move_id' : id_created_header.id,
                        'account_id': record.production_id.product_id.property_stock_production.valuation_in_account_id.id,
                        'analytic_account_id' : analytic_account,
                        'product_id': record.production_id.product_id.id,
                        'name' : " ".join(("Direct Variable Costs", record.name)),
                        'quantity': record.qty_output_wo,
                        'product_uom_id': record.production_id.product_uom_id.id,
                        'credit': 0.0,
                        'debit': amount_variable,
                        #'manufacture_order_id': record.production_id.id,
                    })
                if amount_fixed:
                    id_credit_item_fixed = self.env['account.move.line'].with_context(check_move_validity=False).create({
                        'move_id' : id_created_header.id,
                        'account_id': fixed_account_id.id,
                        'product_id': record.production_id.product_id.id,
                        'name' : " ".join(("Direct Fixed Costs", record.name)),
                        'quantity': record.qty_output_wo,
                        'product_uom_id': record.production_id.product_uom_id.id,
                        'credit': amount_fixed,
                        'debit': 0.0,
                        #'manufacture_order_id': record.production_id.id,
                    })
                    id_debit_item_fixed = self.env['account.move.line'].with_context(check_move_validity=False).create({
                        'move_id' : id_created_header.id,
                        'account_id': record.production_id.product_id.property_stock_production.valuation_in_account_id.id,
                        'analytic_account_id' : analytic_account,
                        'product_id': record.production_id.product_id.id,
                        'name' : " ".join(("Direct Fixed Costs", record.name)),
                        'quantity': record.qty_output_wo,
                        'product_uom_id': record.production_id.product_uom_id.id,
                        'credit': 0.0,
                        'debit': amount_fixed,
                        #'manufacture_order_id': record.production_id.id,
                    })
                    id_created_header.post()
        return True