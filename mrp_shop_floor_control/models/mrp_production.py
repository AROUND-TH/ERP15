# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta
from datetime import datetime, date, timedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero, float_round


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    PLANNING_MODE = [
        ('F', 'Forward'),
        ('B', 'Backward'),
    ]

    # Odoo Standard
    lot_producing_id = fields.Many2one(states={'done': [('readonly', True)]})
    user_id = fields.Many2one(states={'done': [('readonly', True)]})
    # SFC
    planning_mode = fields.Selection(PLANNING_MODE, 'Planning Mode', default="F", required=True, readonly=True, states={'draft': [('readonly', False)], 'confirmed': [('readonly', False)]})
    date_planned_start_pivot = fields.Datetime('Planned Start Pivot Date', readonly=True, states={'draft': [('readonly', False)], 'confirmed': [('readonly', False)]}, default=lambda self: fields.datetime.now())
    date_planned_finished_pivot = fields.Datetime('Planned End Pivot Date', readonly=True, states={'draft': [('readonly', False)], 'confirmed': [('readonly', False)]}, compute='_compute_planned_pivot_finished_date', store=True)
    date_planned_start_wo = fields.Datetime("Scheduled Start Date", readonly=True, copy=False)
    date_planned_finished_wo = fields.Datetime("Scheduled End Date", readonly=True, copy=False)
    date_actual_start_wo = fields.Datetime('Start Date', copy=False, readonly=True, compute="get_actual_dates", store=True)
    date_actual_finished_wo = fields.Datetime('End Date', copy=False, readonly=True, compute="get_actual_dates", store=True)
    origin = fields.Char(readonly=True, states={'draft': [('readonly', False)]})
    is_scheduled = fields.Boolean('Its Operations are Scheduled', compute='_compute_is_scheduled', store=True)
    # Time Management
    hours_uom = fields.Many2one('uom.uom', 'Hours', compute="_get_uom_hours")
    std_setup_time = fields.Float('Total Setup Time', compute='_get_standard_times', digits=(16, 2))
    std_teardown_time = fields.Float('Total Cleanup Time', compute='_get_standard_times', digits=(16, 2))
    std_working_time = fields.Float('Total Working Time', compute='_get_standard_times', digits=(16, 2))
    std_overall_time = fields.Float('Overall Time', compute='_get_standard_times', digits=(16, 2))
    planned_duration_expected = fields.Float('Planned Times', copy=False, readonly=True, digits=(16, 2))
    unplanned_duration_expected = fields.Float('Unplanned Times', copy=False, readonly=True, digits=(16, 2))
    act_setup_time = fields.Float('Total Setup Time', compute='_get_actual_times', digits=(16, 2))
    act_teardown_time = fields.Float('Total Cleanup Time', compute='_get_actual_times', digits=(16, 2))
    act_working_time = fields.Float('Total Working Time', compute='_get_actual_times', digits=(16, 2))
    act_overall_time = fields.Float('Overall Time', compute='_get_actual_times', digits=(16, 2))
    qty_confirmed = fields.Float('Confirmed Qty', digits='Product Unit of Measure', copy=False, readonly=True)

    @api.onchange('planning_mode', 'date_planned_start_pivot', 'product_id', 'company_id', 'picking_type_id', 'bom_id')
    def onchange_planning_mode_forward(self):
        for production in self:
            if production.planning_mode == 'F' and production.date_planned_start_pivot:
                production.date_planned_finished_pivot = production.get_planned_pivot_finished_date(production.date_planned_start_pivot)

    @api.onchange('planning_mode', 'date_planned_finished_pivot', 'product_id', 'company_id', 'picking_type_id', 'bom_id')
    def onchange_planning_mode_backward(self):
        for production in self:
            if production.planning_mode == 'B' and production.date_planned_finished_pivot:
                production.date_planned_start_pivot = production.get_planned_pivot_start_date(production.date_planned_finished_pivot)

    @api.depends('date_planned_start_pivot', 'product_id', 'company_id', 'picking_type_id', 'bom_id.type', 'bom_id', 'planning_mode')
    def _compute_planned_pivot_finished_date(self):
        for production in self:
            if production.date_planned_start_pivot and production.planning_mode == 'F':
                production.date_planned_finished_pivot = production.get_planned_pivot_finished_date(production.date_planned_start_pivot)
        return True

    @api.constrains('date_planned_start_pivot', 'date_planned_finished_pivot')
    def check_dates(self):
        for production in self:
            if production.date_planned_finished_pivot and production.date_planned_start_pivot and production.date_planned_start_pivot > production.date_planned_finished_pivot:
                raise UserError(_("Please check planned pivot dates."))
            if production.state not in ('done', 'cancel'):
                production.date_planned_start = production.date_planned_start_pivot
                production.date_planned_finished = production.date_planned_finished_pivot
        return True

    def get_planned_pivot_finished_date(self, date_start):
        for production in self:
            if production.bom_id.type == 'subcontract':
                subcontractor = production.procurement_group_id.partner_id
                subs = production.bom_id.product_id.seller_ids.filtered(lambda sub: sub.name == subcontractor) or production.bom_id.product_tmpl_id.seller_ids.filtered(lambda sub: sub.name in subcontractor)
                if subs:
                    supplier_delay = subs[0].delay or 1.0
                else:
                    supplier_delay = 1.0
                date_finished = date_start + timedelta(days=supplier_delay)
            else:
                date_finished = date_start + relativedelta(days=production.product_id.produce_delay + 1)
                if production.company_id.manufacturing_lead > 0:
                    date_finished = date_finished + relativedelta(days=production.company_id.manufacturing_lead + 1)
                if production.picking_type_id.warehouse_id.calendar_id:
                    calendar = production.picking_type_id.warehouse_id.calendar_id
                    date_start = calendar.plan_hours(0.0, date_start, True)
                    date_finished = calendar.plan_days(int(production.product_id.produce_delay) + 1, date_start, True)
                    if production.company_id.manufacturing_lead > 0:
                        date_finished = calendar.plan_days(int(production.company_id.manufacturing_lead)  + 1, date_finished, True)
                if date_finished == date_start:
                    date_finished = date_start + relativedelta(hours=1)
        return date_finished

    def get_planned_pivot_start_date(self, date_finished):
        for production in self:
            if production.bom_id.type == 'subcontract':
                subcontractor = production.procurement_group_id.partner_id
                subs = production.bom_id.product_id.seller_ids.filtered(lambda sub: sub.name == subcontractor) or production.bom_id.product_tmpl_id.seller_ids.filtered(lambda sub: sub.name in subcontractor)
                if subs:
                    supplier_delay = subs[0].delay or 1.0
                else:
                    supplier_delay = 1.0
                date_start =  date_finished - timedelta(days=supplier_delay)
            else:
                date_start = date_finished - relativedelta(days=production.product_id.produce_delay + 1)
                if production.company_id.manufacturing_lead > 0:
                    date_start = date_start - relativedelta(days=production.company_id.manufacturing_lead + 1)
                if production.picking_type_id.warehouse_id.calendar_id:
                    calendar = production.picking_type_id.warehouse_id.calendar_id
                    date_finished = calendar.plan_hours(0.0, date_finished, True)
                    date_start = calendar.plan_days(-int(production.product_id.produce_delay) - 1, date_finished, True)
                    if production.company_id.manufacturing_lead > 0:
                        date_start = calendar.plan_days(-int(production.company_id.manufacturing_lead) - 1, date_start, True)
                if date_finished == date_start:
                    date_start =  date_finished - relativedelta(hours=1)
        return date_start

    def _generate_backorder_productions(self, close_mo=True):
        backorders = super()._generate_backorder_productions(close_mo)
        for backorder in backorders:
            backorder.qty_producing = 0
            backorder.state = 'confirmed'
        for workorder in backorders.workorder_ids:
            workorder.qty_produced = 0
            workorder.qty_producing = 0
        return backorders

    def action_capacity_check(self):
        return {
            'name': _('Capacity Check'),
            'view_mode': 'form',
            'res_model': 'mrp.capacity.check',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def action_confirm(self):
        receipt_move = delivery_picking = False
        planned_duration_expected = unplanned_duration_expected = 0.0
        res = super().action_confirm()
        for production in self:
            if production.bom_id.type == 'subcontract':
                subcontractor = production.procurement_group_id.partner_id
                subs = production.bom_id.product_id.seller_ids.filtered(lambda sub: sub.name == subcontractor) or production.bom_id.product_tmpl_id.seller_ids.filtered(lambda sub: sub.name in subcontractor)
                if subs:
                    supplier_delay = subs[0].delay or 1.0
                else:
                    supplier_delay = 1.0
                receipt_move = self.env['stock.move'].search([('reference', '=', production.procurement_group_id.name)], limit=1)
                if receipt_move:
                    date_finished = receipt_move.date
                    date_start = date_finished - timedelta(days=supplier_delay)
                    production.date_planned_start_pivot = date_start
                    receipt_move.date_deadline = receipt_move.date
                delivery_picking = self.env['stock.picking'].search([
                    ('group_id', '=', production.procurement_group_id.name),
                    ('state', 'not in', ('done', 'cancel')),
                    ('picking_type_id.code', '=', 'outgoing'),
                    ], limit=1)
                if delivery_picking:
                    delivery_picking.scheduled_date = delivery_picking.date_deadline
            for workorder in production.workorder_ids.filtered(lambda r: r.operation_id.id != False):
                planned_duration_expected += workorder.duration_expected
            production.planned_duration_expected = planned_duration_expected / 60
            for workorder in production.workorder_ids.filtered(lambda r: r.operation_id.id == False):
                unplanned_duration_expected += workorder.duration_expected
            production.unplanned_duration_expected = unplanned_duration_expected /60
            production.qty_confirmed = production.product_qty
        return res

    @api.depends("workorder_ids.date_planned_start_wo")
    def _compute_is_scheduled(self):
        for production in self:
            if production.workorder_ids:
                production.is_scheduled = any(workorder.date_planned_start_wo for workorder in production.workorder_ids if workorder.state not in ('done', 'cancel'))
            else:
                production.is_scheduled = False
        return True

    # scheduling
    def schedule_workorders(self):
        max_date_finished = False
        start_date = False
        for production in self:
            production.date_planned_start_wo = False
            production.date_planned_finished_wo = False
            floating_times_id = self.env['mrp.floating.times'].search([('warehouse_id', '=', production.picking_type_id.warehouse_id.id)])
            if not floating_times_id:
                raise UserError(_('Floating Times record has not been created yet for the warehouse: %s')% production.picking_type_id.warehouse_id.name)
            warehouse_calendar = production.picking_type_id.warehouse_id.calendar_id
            start_date = production.date_planned_start_pivot or fields.Datetime.now()
            # Release production
            release_time = floating_times_id.mrp_release_time
            if release_time > 0.0 and warehouse_calendar:
                start_date = warehouse_calendar.plan_hours(release_time, start_date, True)
            # before production
            before_production_time = floating_times_id.mrp_ftbp_time
            if before_production_time > 0.0 and warehouse_calendar:
                start_date = warehouse_calendar.plan_hours(before_production_time, start_date, True)
            production.date_planned_start_wo = start_date
            # workorders scheduling
            first_workorder = production.workorder_ids[0]
            sequence_wo = first_workorder.sequence
            first_workorder.date_planned_start_wo = start_date
            calendar = first_workorder.workcenter_id.resource_calendar_id
            if calendar:
                first_workorder.date_planned_start_wo = calendar.plan_hours(0.0, first_workorder.date_planned_start_wo, True)
            first_workorder.forwards_scheduling()
            max_date_finished = first_workorder.date_planned_finished_wo
            succ_workorders = self.env['mrp.workorder'].search([
                ('production_id', '=', first_workorder.production_id.id),
                ('state', 'in', ('ready','pending', 'waiting')),
                ('sequence', '>=', sequence_wo),
                ]).sorted(key=lambda r: r.sequence)
            if succ_workorders:
                current_workorder = first_workorder
                for succ_workorder in succ_workorders:
                    # workorder in parallelo
                    if current_workorder.sequence == succ_workorder.sequence:
                        succ_workorder.date_planned_start_wo = current_workorder.date_planned_start_wo
                        succ_workorder.forwards_scheduling()
                    # workorder in sequenza
                    else:
                        succ_workorder.date_planned_start_wo = max_date_finished
                        succ_workorder.forwards_scheduling()
                    max_date_finished = max(succ_workorder.date_planned_finished_wo, current_workorder.date_planned_finished_wo)
                    current_workorder = succ_workorder
            # after production
            after_production_time = floating_times_id.mrp_ftap_time
            if after_production_time > 0.0 and warehouse_calendar:
                max_date_finished = warehouse_calendar.plan_hours(after_production_time, max_date_finished, True)
            production.date_planned_finished_wo = max_date_finished
        return True

    def button_plan(self):
        res = super().button_plan()
        for production in self:
            production.schedule_workorders()
            production.move_finished_ids.write({'date': production.date_planned_finished_pivot, 'date_deadline': production.date_planned_finished_pivot})
            production.move_raw_ids.write({'date': production.date_planned_start_pivot, 'date_deadline': production.date_planned_start_pivot})
            for picking in production.picking_ids.filtered(lambda r: r.state not in ('done','cancel')):
                picking.write({'scheduled_date': production.date_planned_start_pivot, 'date_deadline': production.date_planned_start_pivot})
        return res

    # delete capacity load
    def button_unplan(self):
        res = super().button_unplan()
        for production in self:
            for workorder in production.workorder_ids:
                workorder.date_planned_start_wo = False
                workorder.date_planned_finished_wo = False
            wo_capacity_ids = self.env['mrp.workcenter.capacity'].search([('workorder_id', 'in', production.workorder_ids.ids)])
            wo_capacity_ids.unlink()
            production.date_planned_start_wo = False
            production.date_planned_finished_wo = False
        return res

    @api.depends('state')
    def get_actual_dates(self):
        for production in self:
            if production.workorder_ids:
                if production.state == "done" and production.workorder_ids:
                    workorders = self.env['mrp.workorder'].search([('production_id', '=', production.id),('state', '=', 'done')])
                    time_records = self.env['mrp.workcenter.productivity'].search([('workorder_id', 'in', workorders.ids)])
                    if time_records:
                        production.date_actual_start_wo = time_records.sorted('date_start')[0].date_start
                        production.date_actual_finished_wo = time_records.sorted('date_end')[-1].date_end
            else:
                if production.state == "confirmed":
                    production.write({'date_actual_start_wo': fields.Datetime.now()})
                if production.state == "done":
                    production.write({'date_actual_finished_wo': fields.Datetime.now()})
        return True

    # delete capacity load
    def action_cancel(self):
        for production in self:
            if production.workorder_ids:
                wo_capacity_ids = self.env['mrp.workcenter.capacity'].search([('workorder_id', 'in', production.workorder_ids.ids)])
                wo_capacity_ids.unlink()
                if any(workorder.state == 'progress' for workorder in production.workorder_ids):
                    raise UserError(_('workorder still running, please close it'))
        return super().action_cancel()

    def button_mark_done(self):
        for production in self:
            if production.workorder_ids:
                if any(workorder.state not in ('done', 'cancel') for workorder in production.workorder_ids):
                    raise UserError(_('workorders not yet processed, please close them before'))
            if production.picking_type_id.active and not production.picking_type_id.warehouse_id.manufacture_steps == 'pbm_sam':
                if any(picking_id.state not in ('done', 'cancel') for picking_id in production.picking_ids):
                    raise UserError(_('pickings not yet processed, please close or cancel them'))
        return super().button_mark_done()

    @api.constrains('date_planned_start_pivot', 'date_planned_finished_pivot', 'state')
    def _align_stock_moves_dates(self):
        for production in self:
            if production.date_planned_finished_pivot and production.date_planned_start_pivot:
                production.move_finished_ids.write({'date': production.date_planned_finished_pivot, 'date_deadline': production.date_planned_finished_pivot})
                production.move_raw_ids.write({'date': production.date_planned_start_pivot, 'date_deadline': production.date_planned_start_pivot})
                pickings = production.picking_ids.filtered(lambda r: r.state not in ('done', 'cancel'))
                if pickings:
                    pickings.write({'scheduled_date': production.date_planned_start_pivot, 'date_deadline': production.date_planned_start_pivot})
                    pickings.move_lines.write({'date': production.date_planned_start_pivot, 'date_deadline': production.date_planned_start_pivot})
        return True

    @api.depends('workorder_ids.state')
    def _get_actual_times(self):
        act_setup_time = act_teardown_time = act_working_time = act_overall_time = 0.0
        for workorder in self.workorder_ids.filtered(lambda r: r.state == "done"):
            for time in workorder.time_ids:
                act_setup_time += time.setup_duration
                act_working_time += time.working_duration
                act_teardown_time += time.teardown_duration
                act_overall_time += time.overall_duration
        self.act_setup_time = act_setup_time / 60
        self.act_teardown_time = act_teardown_time / 60
        self.act_working_time = act_working_time / 60
        self.act_overall_time = act_overall_time / 60
        return True

    def _get_uom_hours(self):
        self.hours_uom = self.env.ref('uom.product_uom_hour', raise_if_not_found=False).id
        return True

    @api.depends('bom_id')
    def _get_standard_times(self):
        std_setup_time = std_teardown_time = std_working_time = 0.0
        for production in self:
            for operation in production.bom_id.operation_ids:
                std_setup_time += operation.workcenter_id.time_start
                std_teardown_time += operation.workcenter_id.time_stop
                cycle_number = float_round(production.product_uom_qty / operation.workcenter_id.capacity, precision_digits=0, rounding_method='UP')
                time_cycle = operation.time_cycle
                std_working_time += cycle_number * time_cycle * 100.0 / operation.workcenter_id.time_efficiency
            production.std_setup_time = std_setup_time / 60
            production.std_teardown_time = std_teardown_time / 60
            production.std_working_time = std_working_time / 60
            production.std_overall_time = (std_setup_time + std_teardown_time + std_working_time) / 60
        return True

    # fix duration expected in backorder generation
    def _generate_backorder_productions(self, close_mo):
        backorders = super()._generate_backorder_productions(close_mo)
        for production in self.procurement_group_id.mrp_production_ids:
            planned_duration_expected = unplanned_duration_expected = 0.0
            for workorder in production.workorder_ids.filtered(lambda r: r.operation_id.id != False):
                workorder.duration_expected = workorder._get_duration_expected()
                planned_duration_expected += workorder.duration_expected
            production.planned_duration_expected = planned_duration_expected / 60
            for workorder in production.workorder_ids.filtered(lambda r: r.operation_id.id == False):
                workorder.duration_expected = workorder._get_duration_expected()
                unplanned_duration_expected += workorder.duration_expected
            production.unplanned_duration_expected = unplanned_duration_expected /60
        backorders.qty_producing = False
        return backorders

    #def button_mark_done(self):
    #    res = super().button_mark_done()
    #    for production in self:
    #        production.move_raw_ids.filtered(lambda m: m.state not in ('done', 'cancel')).write({
    #            'state': 'done',
    #            'product_uom_qty': 0.0,
    #        })
    #    return res
