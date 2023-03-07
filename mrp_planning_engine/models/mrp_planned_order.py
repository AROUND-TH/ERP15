# -*- coding: utf-8 -*-
# Copyright (c) OpenValue All Rights Reserved


from odoo import api, fields, models, _
from datetime import datetime, date, time, timedelta
from odoo.exceptions import UserError


class MrpPlannedOrder(models.Model):
    _name = "mrp.planned.order"
    _description = "MRP Planned Order"
    _order = "order_release_date, id"


    name = fields.Char('Name', copy=False, required=True, readonly=True, default="New")
    mrp_parameter_id = fields.Many2one("mrp.parameter", "MRP Planning Parameters", index=True, required=True)
    warehouse_id = fields.Many2one('stock.warehouse', "Warehouse", related="mrp_parameter_id.warehouse_id", store=True, readonly=True)
    company_id = fields.Many2one("res.company", "Company", related="mrp_parameter_id.warehouse_id.company_id", readonly=True)
    product_id = fields.Many2one("product.product", related="mrp_parameter_id.product_id", store=True, readonly=True)
    product_uom = fields.Many2one("uom.uom", readonly=True, related="product_id.product_tmpl_id.uom_id")
    user_id = fields.Many2one('res.users', string='MRP Planner', related="mrp_parameter_id.user_id", store=True)
    supply_method = fields.Selection(string="MRP Action", related="mrp_parameter_id.supply_method", readonly=True)
    mrp_type = fields.Selection(related="mrp_parameter_id.mrp_type", readonly=True, store=True)
    fixed = fields.Boolean("Fixed", readonly=True, default=True)
    mrp_qty = fields.Float("Planned Quantity", digits='Product Unit of Measure', required=True)
    mrp_element_down_ids = fields.Many2many("mrp.element", string="MRP Element DOWN")
    conversion_indicator = fields.Boolean("Conversion", default=True, readonly=True)
    rescheduled_due_date = fields.Datetime("Rescheduled Due Date", readonly=True)
    forward_planning = fields.Boolean(related="mrp_parameter_id.warehouse_id.company_id.forward_planning", store=True)
    forward_mode_indicator = fields.Boolean("Forward Mode")
    order_release_date = fields.Datetime("Planned Release Date", compute="_get_order_release_date", store=True, readonly=False)
    due_date = fields.Datetime("Planned Due Date")
    delay = fields.Char("Delay (Days)", compute="_get_delay")
    # MTO management
    mto_origin = fields.Char('MTO Origin', readonly=True)
    demand_indicator = fields.Selection(related="mrp_parameter_id.demand_indicator")


    @api.depends("forward_planning", "due_date", "rescheduled_due_date", "order_release_date")
    def _get_delay(self):
        for order in self:
            order.delay = False
            if order.forward_planning and order.rescheduled_due_date and order.due_date:
                delay_timedelta = (order.due_date - order.rescheduled_due_date).days
                order.delay = str(delay_timedelta) if float(delay_timedelta) > 0.0 else False
            elif not order.forward_planning and order.order_release_date:
                delay_timedelta = (datetime.now() - order.order_release_date).days
                order.delay = str(delay_timedelta) if float(delay_timedelta) > 0.0 else False
        return True

    @api.model
    def _create_sequence(self, vals):
        if not vals.get('name') or vals.get('name') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('mrp.planned.order') or 'New'
        return vals

    @api.model
    def create(self, vals):
        vals = self._create_sequence(vals)
        res = super().create(vals)
        return res

    @api.onchange('forward_mode_indicator', 'order_release_date', 'mrp_parameter_id')
    def onchange_planning_mode_forward(self):
        for order in self:
            if order.forward_mode_indicator and order.order_release_date:
                order.due_date = order.mrp_parameter_id._get_finish_date(order.order_release_date)

    @api.onchange('forward_mode_indicator', 'due_date', 'mrp_parameter_id')
    def onchange_planning_mode_backward(self):
        for order in self:
            if not order.forward_mode_indicator and order.due_date:
                order.order_release_date = order.mrp_parameter_id._get_start_date(order.due_date)

    @api.constrains('order_release_date', 'due_date')
    def check_dates(self):
        for order in self:
            if order.due_date and order.order_release_date and order.order_release_date > order.due_date:
                raise UserError(_("Please check dates."))
        return True

    @api.depends("due_date", "mrp_parameter_id")
    def _get_order_release_date(self):
        for order in self:
            if order.due_date and not order.forward_mode_indicator:
                order.order_release_date = order.mrp_parameter_id._get_start_date(order.due_date)
        return True

    def action_toggle_fixed(self):
        for record in self:
            record.fixed = not record.fixed
            record.mrp_element_down_ids.fixed = record.fixed
        return True

    def mrp_convert_planned_order(self):
        self._mrp_convert_planned_order()
        return {"type": "ir.actions.act_window_close"}

    def _mrp_convert_planned_order(self):
        for order in self:
            values = {}
            try:
                if not order.mrp_qty > 0.0:
                    raise UserError(_("Quantity has to be positive."))
                if not order.conversion_indicator:
                    raise UserError(_("Planned Order Conversion is not allowed; please check the Demand Management Indicator"))
                if order.supply_method == "manufacture":
                    bom = order.mrp_parameter_id.bom_id
                    if not bom:
                        raise UserError(_("BoM not found."))
                    if not order.warehouse_id.calendar_id:
                        raise UserError(_("Working Calendar not assigned to Warehouse %s.")% record.warehouse_id.name)
                    mo_data = order._get_mo_data(bom)
                    mo = self.env['mrp.production'].create(mo_data)
                    mo.date_planned_finished_pivot = order.warehouse_id.calendar_id.plan_hours(0.0, order.due_date, True)
                    mo.action_confirm()
                    if mo:
                        order.mrp_element_down_ids.unlink()
                        order.unlink()
                else:
                    values["date_planned"] = order.due_date
                    values["mto_origin"] = order.mto_origin
                    id_created = self.env['procurement.group'].run([self.env['procurement.group'].Procurement(
                        order.product_id,
                        order.mrp_qty,
                        order.product_uom,
                        order.warehouse_id.lot_stock_id,
                        #"Engine: " + str(fields.date.today()),
                        str(order.name),
                        "Engine: " + str(fields.date.today()),
                        order.company_id,
                        values,
                        )], raise_user_error=True)
                    if id_created and order.supply_method == "transfer":
                        move = self.env['stock.move'].search([('name', '=', order.name)])
                        if move:
                            current_move = move
                            while current_move.move_orig_ids:
                                current_move.move_orig_ids.write({'date': order.order_release_date})
                                current_move.move_orig_ids.picking_id.write({'scheduled_date': order.order_release_date})
                                move_ids = current_move.mapped('move_orig_ids')
                                if move_ids:
                                    current_move = move_ids[0]
                                else:
                                    current_move = False
                    if id_created:
                        order.mrp_element_down_ids.unlink()
                        order.unlink()
            except UserError as error:
                if error:
                    model_id = self.env['ir.model'].search([('model', '=', 'mrp.parameter')]).id
                    activity = self.env['mail.activity'].search([('res_id', '=', order.mrp_parameter_id.id), ('res_model_id', '=', model_id), ('note', '=', error.args[0])])
                    if not activity:
                        order.mrp_parameter_id.activity_schedule('mail.mail_activity_data_warning', note=error.args[0], user_id=order.mrp_parameter_id.user_id.id)
        return True

    def _get_mo_data(self, bom):
        for order in self:
            if order.mrp_parameter_id.mrp_type == 'M':
                planning_mode = 'B'
            else:
                planning_mode = 'F'
            return {
                'origin': "MRP: " + str(fields.date.today()),
                'product_id': order.product_id.id,
                'product_qty': order.mrp_qty,
                'product_uom_id': order.product_uom.id,
                'location_src_id': order.warehouse_id.manu_type_id.default_location_src_id.id,
                'location_dest_id': order.warehouse_id.manu_type_id.default_location_dest_id.id,
                'bom_id': bom.id,
                'date_deadline': order.due_date,
                'date_planned_start': order.order_release_date,
                'date_planned_start_pivot': order.order_release_date,
                'planning_mode': planning_mode,
                'procurement_group_id': False,
                'picking_type_id': order.warehouse_id.manu_type_id.id,
                'company_id': order.company_id.id,
                'user_id': order.mrp_parameter_id.user_id.id,
                'mrp_planning_engine': True,
                'mto_origin': order.mto_origin,
            }

    @api.constrains('mrp_qty', 'mrp_parameter_id', 'order_release_date')
    def explode_action(self):
        for order in self:
            bom = False
            if order.mrp_parameter_id._to_be_exploded():
                order.mrp_element_down_ids.unlink()
                mrp_date_supply = order.order_release_date
                if order.mrp_parameter_id.supply_method == "manufacture":
                    bom = order.mrp_parameter_id.bom_id
                elif order.mrp_parameter_id.supply_method == "subcontracting":
                    bom = self.env['mrp.bom']._bom_subcontract_find(
                        product = order.mrp_parameter_id.product_id,
                        picking_type = None,
                        company_id = order.mrp_parameter_id.warehouse_id.company_id.id,
                        bom_type = 'subcontract',
                        subcontractor = order.mrp_parameter_id.main_supplier_id,
                    )
                if not bom:
                    return True
                for bomline in bom.bom_line_ids:
                    if bomline.product_qty <= 0.00 or bomline.product_id.type != "product" or not mrp_date_supply:
                        continue
                    element_data = order._prepare_mrp_element_data_bom_explosion(order, bomline)
                    if element_data:
                        mrp_element = self.env["mrp.element"].create(element_data)
                        order.mrp_element_down_ids = [(4, mrp_element.id)]
        return True

    def _prepare_mrp_element_data_bom_explosion(self, order, bomline):
        parent_product = order.mrp_parameter_id.product_id
        factor = (parent_product.product_tmpl_id.uom_id._compute_quantity(order.mrp_qty, bomline.bom_id.product_uom_id) / bomline.bom_id.product_qty)
        line_quantity = factor * bomline.product_qty
        bomline_mrp_parameter_id = self.env["mrp.parameter"].search([("product_id", "=", bomline.product_id.id),("warehouse_id", "=", order.mrp_parameter_id.warehouse_id.id)], limit=1)
        if bomline_mrp_parameter_id:
            return {
                "product_id": bomline.product_id.id,
                "mrp_parameter_id": bomline_mrp_parameter_id.id,
                "production_id": None,
                "purchase_order_id": None,
                "purchase_line_id": None,
                "stock_move_id": None,
                "mrp_qty": -line_quantity,
                "mrp_date": order.order_release_date.date(),
                "mrp_type": "d",
                "mrp_origin": "mrp",
                "mrp_order_number": self.name,
                "parent_product_id": parent_product.id,
                "note": "Demand BoM Explosion: %s" % parent_product.name,
                "fixed": order.fixed,
                "mto_origin": order.mto_origin,
            }
        else:
            return False

    @api.constrains('mrp_qty', 'mrp_parameter_id', 'order_release_date')
    def transfer_requirement_action(self):
        for order in self:
            if order.mrp_parameter_id.supply_method == 'transfer':
                order.mrp_element_down_ids.unlink()
                mrp_date_supply = order.order_release_date
                element_data = order._prepare_mrp_element_data_stock_transfer(order.mrp_parameter_id, order.mrp_qty, mrp_date_supply)
                if element_data:
                    mrp_element = self.env["mrp.element"].create(element_data)
                    order.mrp_element_down_ids = [(4, mrp_element.id)]
        return True

    def _prepare_mrp_element_data_stock_transfer(self, mrp_parameter_id, qty, mrp_date_demand):
        stock_transfer_mrp_parameter_id = self.env["mrp.parameter"].search([
            ("product_id", "=", mrp_parameter_id.product_id.id),
            ("warehouse_id", "=", mrp_parameter_id.source_warehouse_id.id),
            ], limit=1)
        if stock_transfer_mrp_parameter_id:
            return {
                "product_id": stock_transfer_mrp_parameter_id.product_id.id,
                "mrp_parameter_id": stock_transfer_mrp_parameter_id.id,
                "production_id": None,
                "purchase_order_id": None,
                "purchase_line_id": None,
                "stock_move_id": None,
                "mrp_qty": -qty,
                "mrp_date": mrp_date_demand.date(),
                "mrp_type": "d",
                "mrp_origin": "st",
                "mrp_order_number": self.name,
                "parent_product_id": None,
                "note": "Demand Stock Transfer: %s" % stock_transfer_mrp_parameter_id.warehouse_id.name,
                "fixed": self.fixed,
            }
        else:
            return False

    def unlink(self):
        for order in self:
            order.mrp_element_down_ids.unlink()
            mrp_elements = self.env["mrp.element"].search([("mrp_order_number", "=", order.name)])
            mrp_elements.unlink()
        return super().unlink()
