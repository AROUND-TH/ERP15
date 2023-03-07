# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
from datetime import date

from odoo.tools import float_round


class MrpProduction(models.Model):
    _inherit = 'mrp.production'


    closure_state = fields.Boolean('Financial Closure', copy=False, default=False)
    # overheads
    ovh_var_direct_cost = fields.Float('OVH Variable Direct Cost', digits='Product Price', readonly=True, copy=False)
    ovh_fixed_direct_cost = fields.Float('OVH Fixed Direct Cost', digits='Product Price', readonly=True, copy=False)
    ovh_product_cost = fields.Float('OVH Finished Product Cost', digits='Product Price', readonly=True, copy=False)
    ovh_components_cost = fields.Float('OVH Components Cost', digits='Product Price', readonly=True, copy=False)
    industrial_cost = fields.Float('Actual Full Industrial Cost', digits='Product Price', readonly=True, copy=False)
    industrial_cost_unit = fields.Float(' Actual Full Industrial Unit Cost', digits='Product Price', group_operator="avg", readonly=True, copy=False)


    def button_mark_done(self):
        # @Overheads Cost Calculation
        self._wc_ovh_analytic_postings(posting=False)
        self._bom_ovh_analytic_postings(posting=False)
        # @Set Master Product Cost with Current Standard Cost
        self._set_standard_price_cost()

        action = super().button_mark_done()
        for move in self.move_raw_ids:
            if move.analytic_account_line_id:
                analytic_line = self.env['account.analytic.line'].browse(move.analytic_account_line_id.id)
                analytic_line.sudo().unlink()
        for workorder in self.workorder_ids:
            if workorder.mo_analytic_account_line_id:
                analytic_line = self.env['account.analytic.line'].browse(workorder.mo_analytic_account_line_id.id)
                analytic_line.sudo().unlink()
        return action

    def button_closure(self):
        for record in self:
            qty_produced = record._get_qty_produced()

            # variances
            record._planned_variance_postings(qty_produced)
            # @Remark for not use cause duplicate on new Design Spec
            # record._material_costs_variance_postings(qty_produced)
            # record._direct_costs_variance_postings(qty_produced)

            # overheads
            record._wc_ovh_analytic_postings(posting=True)
            record._bom_ovh_analytic_postings(posting=True)

            # delta
            record._delta_costs_variance_postings(qty_produced)

            record.industrial_cost = record.direct_cost + record.ovh_var_direct_cost + record.ovh_fixed_direct_cost + record.ovh_product_cost + record.ovh_components_cost
            record.industrial_cost_unit = record.industrial_cost / qty_produced

            record.closure_state = 'True'
        return True

    def _get_final_date(self):
        final_date = False
        for record in self:
            if record.date_actual_finished_wo:
                final_date = record.date_actual_finished_wo.date()
            else:
                final_date = date.today()
        return final_date

    # production planned variance costs posting
    def _planned_variance_postings(self, quantity):
        standard_cost = planned_cost = 0.0
        for record in self:
            final_date = record._get_final_date()
            standard_cost = record.std_prod_cost
            planned_cost = record.planned_direct_cost_unit
            delta = (planned_cost - standard_cost) * quantity
            desc_bom = str(record.name)
            if delta < 0.0:
                id_created_header = self.env['account.move'].create({
                'journal_id' : record.company_id.manufacturing_journal_id.id,
                'date': final_date,
                'ref' : "Planned Costs Variance",
                'company_id': record.company_id.id,
                'manufacture_order_id': record.id,
                })
                id_credit_item = self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'move_id' : id_created_header.id,
                    'account_id': record.company_id.planned_variances_account_id.id,
                    'product_id': record.product_id.id,
                    'name' : desc_bom,
                    'quantity': quantity,
                    'product_uom_id': record.product_uom_id.id,
                    'credit': - delta,
                    'debit': 0.0,
                    #'manufacture_order_id': record.id,
                })
                id_debit_item= self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'move_id' : id_created_header.id,
                    'account_id': record.product_id.property_stock_production.valuation_out_account_id.id,
                    'analytic_account_id' : record.bom_id.costs_planned_variances_analytic_account_id.id,
                    'product_id': record.product_id.id,
                    'name' : desc_bom,
                    'quantity': quantity,
                    'product_uom_id': record.product_uom_id.id,
                    'credit': 0.0,
                    'debit': - delta,
                    #'manufacture_order_id': record.id,
                })
                id_created_header.action_post()
            elif delta > 0.0:
                id_created_header = self.env['account.move'].create({
                'journal_id' : record.company_id.manufacturing_journal_id.id,
                'date': final_date,
                'ref' : "Planned Costs Variance",
                'company_id': record.company_id.id,
                'manufacture_order_id': record.id,
                })
                id_credit_item = self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'move_id' : id_created_header.id,
                    'account_id': record.product_id.property_stock_production.valuation_out_account_id.id,
                    'analytic_account_id' : record.bom_id.costs_planned_variances_analytic_account_id.id,
                    'product_id': record.product_id.id,
                    'name' : desc_bom,
                    'quantity': quantity,
                    'product_uom_id': record.product_uom_id.id,
                    'credit': delta,
                    'debit': 0.0,
                    #'manufacture_order_id': record.id,
                })
                id_debit_item= self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'move_id' : id_created_header.id,
                    'account_id': record.company_id.planned_variances_account_id.id,
                    'product_id': record.product_id.id,
                    'name' : desc_bom,
                    'quantity': quantity,
                    'product_uom_id': record.product_uom_id.id,
                    'credit': 0.0,
                    'debit': delta,
                    #'manufacture_order_id': record.id,
                })
                id_created_header.action_post()
        return True

    # production material and by product variance costs posting
    def _material_costs_variance_postings(self, quantity):
        mat_actual_amount = mat_planned_amount = matamount = receiptamount = by_product_amount  = 0.0
        for record in self:
            final_date = record._get_final_date()
            raw_moves = record.move_raw_ids.filtered(lambda r: (r.state == 'done' and r.product_id.type == 'product'))
            for move in raw_moves:
                matamount += move.product_id.standard_price * move.product_qty
            finished_moves = record.move_finished_ids.filtered(lambda r: (r.state == 'done' and r.product_id.type == 'product'))
            for move in finished_moves:
                receiptamount += move.product_id.standard_price * move.product_qty
            if receiptamount > 0.0:
                by_product_amount = receiptamount - record.std_prod_cost * quantity
            mat_actual_amount = matamount - by_product_amount
            mat_planned_amount = (record.planned_mat_cost_unit - record.planned_byproduct_amount_unit) * quantity
            delta = mat_actual_amount - mat_planned_amount
            desc_bom = str(record.name)
            if delta < 0.0:
                id_created_header = self.env['account.move'].create({
                    'journal_id' : record.company_id.manufacturing_journal_id.id,
                    'date': final_date,
                    'ref' : "Material and By Products Variance",
                    'company_id': record.company_id.id,
                    'manufacture_order_id': record.id,
                })
                id_credit_item = self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'move_id' : id_created_header.id,
                    'account_id': record.company_id.material_variances_account_id.id,
                    'product_id': record.product_id.id,
                    'name' : desc_bom,
                    'quantity': quantity,
                    'product_uom_id': record.product_uom_id.id,
                    'credit': - delta,
                    'debit': 0.0,
                    #'manufacture_order_id': record.id,
                })
                id_debit_item= self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'move_id' : id_created_header.id,
                    'account_id': record.product_id.property_stock_production.valuation_out_account_id.id,
                    'analytic_account_id' : record.bom_id.costs_material_variances_analytic_account_id.id,
                    'product_id': record.product_id.id,
                    'name' : desc_bom,
                    'quantity': quantity,
                    'product_uom_id': record.product_uom_id.id,
                    'credit': 0.0,
                    'debit': - delta,
                    #'manufacture_order_id': record.id,
                })
                id_created_header.action_post()
            elif delta > 0.0:
                id_created_header = self.env['account.move'].create({
                    'journal_id' : record.company_id.manufacturing_journal_id.id,
                    'date': final_date,
                    'ref' : "Material and By Products Variance",
                    'company_id': record.company_id.id,
                    'manufacture_order_id': record.id,
                })
                id_credit_item = self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'move_id' : id_created_header.id,
                    'account_id': record.product_id.property_stock_production.valuation_out_account_id.id,
                    'analytic_account_id' : record.bom_id.costs_material_variances_analytic_account_id.id,
                    'product_id': record.product_id.id,
                    'name' : desc_bom,
                    'quantity': quantity,
                    'product_uom_id': record.product_uom_id.id,
                    'credit': delta,
                    'debit': 0.0,
                    #'manufacture_order_id': record.id,
                })
                id_debit_item= self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'move_id' : id_created_header.id,
                    'account_id': record.company_id.material_variances_account_id.id,
                    'product_id': record.product_id.id,
                    'name' : desc_bom,
                    'quantity': quantity,
                    'product_uom_id': record.product_uom_id.id,
                    'credit': 0.0,
                    'debit': delta,
                    #'manufacture_order_id': record.id,
                })
                id_created_header.action_post()
        return True

    # production direct variance costs posting
    def _direct_costs_variance_postings(self, quantity):
        direct_actual_amount = direct_planned_amount = 0.0
        for record in self:
            final_date = record._get_final_date()
            direct_actual_amount = (record.var_cost_unit + record.fixed_cost_unit) * quantity
            direct_planned_amount =  (record.planned_var_cost_unit + record.planned_fixed_cost_unit) * quantity
            delta = direct_actual_amount - direct_planned_amount
            desc_bom = str(record.name)
            if delta < 0.0:
                id_created_header = self.env['account.move'].create({
                    'journal_id' : record.company_id.manufacturing_journal_id.id,
                    'date': final_date,
                    'ref' : "Direct Costs Variance",
                    'company_id': record.company_id.id,
                    'manufacture_order_id': record.id,
                })
                id_credit_item = self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'move_id' : id_created_header.id,
                    'account_id': record.company_id.other_variances_account_id.id,
                    'product_id': record.product_id.id,
                    'name' : desc_bom,
                    'quantity': quantity,
                    'product_uom_id': record.product_uom_id.id,
                    'credit': - delta,
                    'debit': 0.0,
                    #'manufacture_order_id': record.id,
                })
                id_debit_item= self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'move_id' : id_created_header.id,
                    'account_id': record.product_id.property_stock_production.valuation_out_account_id.id,
                    'analytic_account_id' : record.bom_id.costs_direct_variances_analytic_account_id.id,
                    'product_id': record.product_id.id,
                    'name' : desc_bom,
                    'quantity': quantity,
                    'product_uom_id': record.product_uom_id.id,
                    'credit': 0.0,
                    'debit': - delta,
                    #'manufacture_order_id': record.id,
                })
                id_created_header.action_post()
            elif delta > 0.0:
                id_created_header = self.env['account.move'].create({
                    'journal_id' : record.company_id.manufacturing_journal_id.id,
                    'date': final_date,
                    'ref' : "Direct Costs Variance",
                    'company_id': record.company_id.id,
                })
                id_credit_item = self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'move_id' : id_created_header.id,
                    'account_id': record.product_id.property_stock_production.valuation_out_account_id.id,
                    'analytic_account_id' : record.bom_id.costs_direct_variances_analytic_account_id.id,
                    'product_id': record.product_id.id,
                    'name' : desc_bom,
                    'quantity': quantity,
                    'product_uom_id': record.product_uom_id.id,
                    'credit': delta,
                    'debit': 0.0,
                    #'manufacture_order_id': record.id,
                })
                id_debit_item= self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'move_id' : id_created_header.id,
                    'account_id': record.company_id.other_variances_account_id.id,
                    'product_id': record.product_id.id,
                    'name' : desc_bom,
                    'quantity': quantity,
                    'product_uom_id': record.product_uom_id.id,
                    'credit': 0.0,
                    'debit': delta,
                    #'manufacture_order_id': record.id,
                })
                id_created_header.action_post()
        return True


    # production delta costs posting
    def _delta_costs_variance_postings(self, quantity):
        for record in self:
            final_date = record._get_final_date()
            desc_bom = str(record.name)

            # delta_var_cost posting (Delta Direct Variable Cost)
            if record.delta_var_cost < 0.0:
                id_created_header = self.env['account.move'].create({
                    'journal_id' : record.company_id.manufacturing_journal_id.id,
                    'date': final_date,
                    'ref' : "Delta Direct Variable Cost",
                    'company_id': record.company_id.id,
                    'manufacture_order_id': record.id,
                })
                id_debit_item= self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'move_id' : id_created_header.id,
                    'account_id': record.product_id.property_stock_production.valuation_out_account_id.id,
                    'analytic_account_id' : record.bom_id.costs_direct_variances_analytic_account_id.id,
                    'product_id': record.product_id.id,
                    'name' : desc_bom,
                    'quantity': quantity,
                    'product_uom_id': record.product_uom_id.id,
                    'credit': 0.0,
                    'debit': - record.delta_var_cost,
                    #'manufacture_order_id': record.id,
                })
                id_credit_item = self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'move_id' : id_created_header.id,
                    'account_id': record.company_id.other_variances_account_id.id,
                    'product_id': record.product_id.id,
                    'name' : desc_bom,
                    'quantity': quantity,
                    'product_uom_id': record.product_uom_id.id,
                    'credit': - record.delta_var_cost,
                    'debit': 0.0,
                    #'manufacture_order_id': record.id,
                })
                id_created_header.action_post()
            elif record.delta_var_cost > 0.0:
                id_created_header = self.env['account.move'].create({
                    'journal_id' : record.company_id.manufacturing_journal_id.id,
                    'date': final_date,
                    'ref' : "Delta Direct Variable Cost",
                    'company_id': record.company_id.id,
                })
                id_debit_item= self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'move_id' : id_created_header.id,
                    'account_id': record.company_id.other_variances_account_id.id,
                    'product_id': record.product_id.id,
                    'name' : desc_bom,
                    'quantity': quantity,
                    'product_uom_id': record.product_uom_id.id,
                    'credit': 0.0,
                    'debit': record.delta_var_cost,
                    #'manufacture_order_id': record.id,
                })
                id_credit_item = self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'move_id' : id_created_header.id,
                    'account_id': record.product_id.property_stock_production.valuation_out_account_id.id,
                    'analytic_account_id' : record.bom_id.costs_direct_variances_analytic_account_id.id,
                    'product_id': record.product_id.id,
                    'name' : desc_bom,
                    'quantity': quantity,
                    'product_uom_id': record.product_uom_id.id,
                    'credit': record.delta_var_cost,
                    'debit': 0.0,
                    #'manufacture_order_id': record.id,
                })
                id_created_header.action_post()

            # delta_fixed_cost posting (Delta Direct Fixed Cost)
            if record.delta_fixed_cost < 0.0:
                id_created_header = self.env['account.move'].create({
                    'journal_id' : record.company_id.manufacturing_journal_id.id,
                    'date': final_date,
                    'ref' : "Delta Direct Fixed Cost",
                    'company_id': record.company_id.id,
                    'manufacture_order_id': record.id,
                })
                id_debit_item= self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'move_id' : id_created_header.id,
                    'account_id': record.product_id.property_stock_production.valuation_out_account_id.id,
                    'analytic_account_id' : record.bom_id.costs_direct_variances_analytic_account_id.id,
                    'product_id': record.product_id.id,
                    'name' : desc_bom,
                    'quantity': quantity,
                    'product_uom_id': record.product_uom_id.id,
                    'credit': 0.0,
                    'debit': - record.delta_fixed_cost,
                    #'manufacture_order_id': record.id,
                })
                id_credit_item = self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'move_id' : id_created_header.id,
                    'account_id': record.company_id.other_fixed_account_id.id,
                    'product_id': record.product_id.id,
                    'name' : desc_bom,
                    'quantity': quantity,
                    'product_uom_id': record.product_uom_id.id,
                    'credit': - record.delta_fixed_cost,
                    'debit': 0.0,
                    #'manufacture_order_id': record.id,
                })
                id_created_header.action_post()
            elif record.delta_fixed_cost > 0.0:
                id_created_header = self.env['account.move'].create({
                    'journal_id' : record.company_id.manufacturing_journal_id.id,
                    'date': final_date,
                    'ref' : "Delta Direct Fixed Cost",
                    'company_id': record.company_id.id,
                })
                id_debit_item= self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'move_id' : id_created_header.id,
                    'account_id': record.company_id.other_fixed_account_id.id,
                    'product_id': record.product_id.id,
                    'name' : desc_bom,
                    'quantity': quantity,
                    'product_uom_id': record.product_uom_id.id,
                    'credit': 0.0,
                    'debit': record.delta_fixed_cost,
                    #'manufacture_order_id': record.id,
                })
                id_credit_item = self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'move_id' : id_created_header.id,
                    'account_id': record.product_id.property_stock_production.valuation_out_account_id.id,
                    'analytic_account_id' : record.bom_id.costs_direct_variances_analytic_account_id.id,
                    'product_id': record.product_id.id,
                    'name' : desc_bom,
                    'quantity': quantity,
                    'product_uom_id': record.product_uom_id.id,
                    'credit': record.delta_fixed_cost,
                    'debit': 0.0,
                    #'manufacture_order_id': record.id,
                })
                id_created_header.action_post()

        return True


    ##### @Overheads Cost functions

    def _wc_ovh_analytic_postings(self, posting):
        fixedamount = varamount = 0.0
        for record in self:
            final_date = record._get_final_date()
            for workorder in record.workorder_ids:
                desc_wo = str(record.name) + '-' + str(workorder.workcenter_id.name) + '-' + str(workorder.name)
                for time in workorder.time_ids:
                    if time.overall_duration:
                        varamount += time.working_duration * workorder.workcenter_id.costs_hour / 60 * workorder.workcenter_id.costs_overhead_variable_percentage / 100
                        fixedamount += (time.setup_duration + time.teardown_duration) * workorder.workcenter_id.costs_hour_fixed / 60 * workorder.workcenter_id.costs_overhead_fixed_percentage / 100
                    else:
                        varamount += time.duration * workorder.workcenter_id.costs_hour / 60 * workorder.workcenter_id.costs_overhead_variable_percentage / 100

                if (posting == True):
                    # fixed direct overhead cost posting
                    if fixedamount:
                        id_created= self.env['account.analytic.line'].create({
                            'name': desc_wo,
                            'account_id': workorder.workcenter_id.analytic_account_id.id,
                            'ref': "OVH fixed direct costs",
                            'date': final_date,
                            'product_id': record.product_id.id,
                            'amount': - fixedamount,
                            'unit_amount': workorder.qty_output_wo,
                            'product_uom_id': record.product_uom_id.id,
                            'company_id': workorder.workcenter_id.company_id.id,
                            'manufacture_order_id': record.id,
                        })
                    # variable direct overhead cost posting
                    if varamount:
                        id_created= self.env['account.analytic.line'].create({
                            'name': desc_wo,
                            'account_id': workorder.workcenter_id.analytic_account_id.id,
                            'ref': "OVH variable direct costs",
                            'date': final_date,
                            'product_id': record.product_id.id,
                            'amount': - varamount,
                            'unit_amount': workorder.qty_output_wo,
                            'product_uom_id': record.product_uom_id.id,
                            'company_id': workorder.workcenter_id.company_id.id,
                            'manufacture_order_id': record.id,
                        })
            record.ovh_var_direct_cost = varamount
            record.ovh_fixed_direct_cost = fixedamount
        return True

    def _bom_ovh_analytic_postings(self, posting):
        ovhproductcost = ovhcomponentscost = 0.0
        for record in self:
            final_date = record._get_final_date()
            desc_bom = str(record.name)

            # @Change business logic to use Standard Costs to calculate.
            # ovhproductcost = record.direct_cost * record.bom_id.costs_overhead_product_percentage / 100
            # ovhcomponentscost = record.mat_cost * record.bom_id.costs_overhead_components_percentage / 100
            ovhproductcost = (record.std_direct_cost / record.product_qty) * (record.bom_id.costs_overhead_product_percentage / 100)
            ovhcomponentscost = (record.std_mat_cost / record.product_qty) * (record.bom_id.costs_overhead_components_percentage / 100)

            ovhproductcost = float_round(ovhproductcost, precision_digits=2)
            ovhcomponentscost = float_round(ovhcomponentscost, precision_digits=2)

            if (posting == True):
                # overhead product cost posting
                if ovhproductcost:
                    id_created= self.env['account.analytic.line'].create({
                        'name': desc_bom,
                        'account_id': record.bom_id.overhead_analytic_account_id.id,
                        'ref': "OVH production costs",
                        'date': final_date,
                        'product_id': record.product_id.id,
                        'amount': - ovhproductcost,
                        'unit_amount': record.product_qty,
                        'product_uom_id': record.product_uom_id.id,
                        'company_id': record.company_id.id,
                        'manufacture_order_id': record.id,
                    })
                # overhead components cost posting
                if ovhcomponentscost:
                    id_created= self.env['account.analytic.line'].create({
                        'name': desc_bom,
                        'account_id': record.bom_id.overhead_analytic_account_id.id,
                        'ref': "OVH components costs",
                        'date': final_date,
                        'product_id': record.product_id.id,
                        'amount': - ovhcomponentscost,
                        'unit_amount': record.product_qty,
                        'product_uom_id': record.product_uom_id.id,
                        'company_id': record.company_id.id,
                        'manufacture_order_id': record.id,
                    })

                # @Post to default journal entry.
                if ovhproductcost or ovhcomponentscost:
                    id_created_header = self.env['account.move'].create({
                    # Revise to "Manufacturing Journal"
                    # 'journal_id' : record.company_id.automatic_entry_default_journal_id.id,
                    'journal_id' : record.company_id.manufacturing_journal_id.id,
                    'date': final_date,
                    'ref' : "Overhead Costs",
                    'company_id': record.company_id.id,
                    'manufacture_order_id': record.id,
                    })
                    id_debit_item = self.env['account.move.line'].with_context(check_move_validity=False).create({
                        'move_id' : id_created_header.id,
                        # @Set to "114030 งานระหว่างทำ"
                        # 'account_id': record.product_id.categ_id.property_stock_account_output_categ_id.id,
                        'account_id': record.product_id.property_stock_production.valuation_in_account_id.id,
                        'analytic_account_id' : record.bom_id.overhead_analytic_account_id.id,
                        'product_id': record.product_id.id,
                        'name' : desc_bom,
                        'quantity': record.product_qty,
                        'product_uom_id': record.product_uom_id.id,
                        'credit': 0.0,
                        'debit': (ovhproductcost + ovhcomponentscost) * record.product_qty,
                        #'manufacture_order_id': record.id,
                    })
                    id_credit_item = self.env['account.move.line'].with_context(check_move_validity=False).create({
                        'move_id' : id_created_header.id,
                        # @Set to "518000 ค่าใช้จ่ายในการผลิต"
                        'account_id': record.company_id.journal_production_cost_account_id.id,
                        'product_id': record.product_id.id,
                        'name' : desc_bom,
                        'quantity': record.product_qty,
                        'product_uom_id': record.product_uom_id.id,
                        'credit': (ovhproductcost + ovhcomponentscost) * record.product_qty,
                        'debit': 0.0,
                        #'manufacture_order_id': record.id,
                    })
                    id_created_header.action_post()

            record.ovh_product_cost = ovhproductcost
            record.ovh_components_cost = ovhcomponentscost
        return True

    def _set_standard_price_cost(self):
        for production in self:
            # @Set Master Product Cost with Current Standard Cost
            production.product_id.standard_price = production.product_id.basic_cost + production.ovh_product_cost + production.ovh_components_cost
            production.product_id.update_standard_price = True
        return True

    ###########################################
