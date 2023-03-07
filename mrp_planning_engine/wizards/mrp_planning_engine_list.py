# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime, date, time, timedelta
import pytz
from pytz import timezone
from odoo.addons.mrp_planning_engine.models.mrp_element import MRP_ORIGIN_SELECTION
from odoo.addons.mrp_planning_engine.models.mrp_element import STATE_SELECTION
from odoo.exceptions import UserError
import logging

logger = logging.getLogger(__name__)


MRP_TYPE_SELECTION = [
    ("s", "Supply"),
    ("d", "Demand"),
    ("f", "Frozen Period"),
    ("b", "Begin"),
    ("e", "End"),
]

class MRPPlanningEngineList(models.TransientModel):
    _name = 'mrp.planning.engine.list'
    _description = 'MRP Planning Engine List'

    name = fields.Char("Name")
    mrp_parameter_id = fields.Many2one("mrp.parameter", "MRP Planning Parameters", required=True)
    item_ids = fields.One2many('mrp.planning.engine.list.item', 'wizard_id')
    user_id = fields.Many2one(related='mrp_parameter_id.user_id')
    trigger = fields.Selection(related='mrp_parameter_id.trigger')
    supply_method = fields.Selection(related='mrp_parameter_id.supply_method')
    mrp_minimum_stock = fields.Float(related='mrp_parameter_id.mrp_minimum_stock')
    mrp_safety_time = fields.Integer(related='mrp_parameter_id.mrp_safety_time')
    product_uom = fields.Many2one(related='mrp_parameter_id.product_uom')
    days_uom = fields.Many2one(related='mrp_parameter_id.days_uom')
    mrp_type = fields.Selection(related='mrp_parameter_id.mrp_type')
    lot_qty_method = fields.Selection(related='mrp_parameter_id.lot_qty_method')
    demand_indicator = fields.Selection(related='mrp_parameter_id.demand_indicator')
    mrp_demand_backward_day = fields.Integer(related='mrp_parameter_id.mrp_demand_backward_day')
    forward_planning = fields.Boolean(related="mrp_parameter_id.warehouse_id.company_id.forward_planning", store=True)

    def name_get(self):
        result = []
        for record in self:
            rec_name = "%s %s-%s" % ("Planning Engine List: ", record.mrp_parameter_id.product_id.name, record.mrp_parameter_id.warehouse_id.name)
            result.append((record.id, rec_name))
        return result

    def update_planning_engine_list(self):
        self.env['mrp.planning.engine.list.item'].search([]).unlink()
        return self.action_planning_engine_list()

    def action_planning_engine_list(self):
        today = date.today()
        today_datetime_utc = datetime(today.year, today.month, today.day)
        today_datetime_utc = timezone('utc').localize(today_datetime_utc)
        today_datetime_utc = today_datetime_utc.astimezone(timezone('UTC')).replace(tzinfo=None)
        user_timezone = self.env['res.users'].browse(self._context.get('uid')).tz
        local_datetime = today_datetime_utc.astimezone(timezone(user_timezone)).replace(tzinfo=None)
        delta_hours = ((today_datetime_utc - local_datetime).total_seconds())/3600
        today_datetime = today_datetime_utc + timedelta(hours=delta_hours)
        for list in self:
            stock_mrp = list.mrp_parameter_id._compute_qty_available()
            id_created_begin = self.env['mrp.planning.engine.list.item'].create({
                'wizard_id' : list.id,
                'mrp_parameter_id' : list.mrp_parameter_id.id,
                'product_id' : list.mrp_parameter_id.product_id.id,
                'mrp_qty' : stock_mrp,
                'mrp_date' : datetime.strptime('1900-01-01','%Y-%m-%d').date(),
                "mrp_type": "b",
                #"fixed": False,
            })
            id_created_end = self.env['mrp.planning.engine.list.item'].create({
                'wizard_id' : list.id,
                'mrp_parameter_id' : list.mrp_parameter_id.id,
                'product_id' : list.mrp_parameter_id.product_id.id,
                'mrp_qty' : 0.0,
                'mrp_date' : datetime.strptime('2999-12-31','%Y-%m-%d').date(),
                "mrp_type": "e",
                #"fixed": False,
            })
            if list.mrp_parameter_id.mrp_frozen_days > 0 and not list.mrp_parameter_id.demand_indicator == "20":
                frozen_date = list.mrp_parameter_id.warehouse_id.calendar_id.plan_days(int(list.mrp_parameter_id.mrp_frozen_days+1), fields.Datetime.now(), True)
                id_created_frozen_period = self.env['mrp.planning.engine.list.item'].create({
                    'wizard_id' : list.id,
                    'mrp_parameter_id' : list.mrp_parameter_id.id,
                    'product_id' : list.mrp_parameter_id.product_id.id,
                    'mrp_qty' : 0.0,
                    'mrp_date' : frozen_date.date(),
                    "mrp_type": "f",
                    #"fixed": False,
                    "note": "--- End of frozen period ---",
                })
        # Demand
        demand_items = self.env["mrp.demand"].search([("mrp_parameter_id", "=", list.mrp_parameter_id.id), ("state", "=", "done")])
        for demand_item in demand_items:
            demand_item_data = demand_item.mrp_parameter_id._prepare_mrp_element_data_from_demand(demand_item)
            demand_item_data['wizard_id'] = list.id
            self.env['mrp.planning.engine.list.item'].create(demand_item_data)
        # RfQs
        location_ids = list.mrp_parameter_id.location_ids
        picking_type_ids = self.env["stock.picking.type"].search([("default_location_dest_id", "in", location_ids.ids), ("code", "=", "incoming")]).ids
        pos = self.env["purchase.order"].search([("picking_type_id", "in", picking_type_ids),("state", "in", ["draft", "sent", "to approve"])])
        po_lines = self.env["purchase.order.line"].search([("order_id", "in", pos.ids), ("product_qty", ">", 0.0),("product_id", "=", list.mrp_parameter_id.product_id.id)])
        for po_line in po_lines:
            rfq_item_data = list.mrp_parameter_id._prepare_mrp_element_data_from_rfq(po_line)
            rfq_item_data['wizard_id'] = list.id
            rfq_item_list = self.env['mrp.planning.engine.list.item'].create(rfq_item_data)
            # exception messages
            # late RfQs
            if po_line.order_id.date_order < today_datetime:
                rfq_item_list.note = 'RfQ document date in the past'
        # Subcontracting RfQ Requirements
        other_po_lines = self.env["purchase.order.line"].search([("order_id", "in", pos.ids), ("product_qty", ">", 0.0), ("product_id", "!=", list.mrp_parameter_id.product_id.id)])
        for other_po_line in other_po_lines:
            other_po_line_mrp_parameter = self.env["mrp.parameter"].search([("product_id", "=", other_po_line.product_id.id),("warehouse_id", "=", list.mrp_parameter_id.warehouse_id.id)], limit=1)
            if other_po_line_mrp_parameter and other_po_line_mrp_parameter.supply_method == 'subcontracting':
                bom = self.env['mrp.bom']._bom_subcontract_find(
                    product = other_po_line.product_id,
                    picking_type = None,
                    company_id = other_po_line.order_id.company_id.id,
                    bom_type = 'subcontract',
                    subcontractor = other_po_line.order_id.partner_id,
                )
                for bomline in bom.bom_line_ids:
                    if bomline.product_id == list.mrp_parameter_id.product_id and not bomline.product_qty <= 0.00:
                        sub_rfq_item_data = list.mrp_parameter_id._prepare_mrp_element_data_from_sub_rfq(self, other_po_line, bomline)
                        sub_rfq_item_data['wizard_id'] = list.id
                        self.env['mrp.planning.engine.list.item'].create(sub_rfq_item_data)
        # stock moves
        in_domain = list.mrp_parameter_id._in_stock_moves_domain()
        in_moves = self.env["stock.move"].search(in_domain)
        if in_moves:
            for move in in_moves:
                in_move_data = list.mrp_parameter_id._prepare_data_from_stock_move(move, direction="in")
                in_move_data['wizard_id'] = list.id
                in_move_item_list = self.env['mrp.planning.engine.list.item'].create(in_move_data)
                # exception messages
                # MOs
                if move.production_id and not (move.production_id.location_dest_id.id == move.production_id.company_id.subcontracting_location_id.id):
                    # late MOs
                    if move.production_id.date_planned_start_pivot < today_datetime and move.production_id.state in ('draft', 'confirmed'):
                        in_move_item_list.note = 'MO late: MO not started and planned pivot start date in the past'
                    # expired MOs
                    elif move.production_id.date_planned_finished_pivot < today_datetime:
                        in_move_item_list.note = 'MO expired: planned pivot finish date in the past'
                    # scheduled MOs
                    elif move.production_id.date_planned_finished_wo and move.production_id.date_planned_finished_pivot < move.production_id.date_planned_finished_wo:
                        in_move_item_list.note = 'MO scheduled finish date overcomes MO planned pivot finish date'
                # POs
                elif move.purchase_line_id:
                    # expired POs
                    if move.purchase_line_id.date_planned < today_datetime:
                        in_move_item_list.note = 'PO Item expired: delivery date in the past'
        logger.info("#####")
        out_domain = list.mrp_parameter_id._out_stock_moves_domain()
        logger.info(out_domain)
        out_moves = self.env["stock.move"].search(out_domain)
        logger.info("#####")
        logger.info(out_moves)
        if out_moves:
            for move in out_moves:
                out_move_data = list.mrp_parameter_id._prepare_data_from_stock_move(move, direction="out")
                out_move_data['wizard_id'] = list.id
                self.env['mrp.planning.engine.list.item'].create(out_move_data)
        # Planned Orders
        for planned_order in list.mrp_parameter_id.planned_order_ids:
            planned_order_data = list.mrp_parameter_id._prepare_mrp_element_data_from_planned_order(planned_order)
            planned_order_data['wizard_id'] = list.id
            planned_order_item_list = self.env['mrp.planning.engine.list.item'].create(planned_order_data)
            # exception messages
            # Planned Orders in forward mode
            if planned_order.mrp_type == "M" and planned_order.forward_mode_indicator:
                planned_order_item_list.note = 'Rescheduling in Forward Mode'
            # expired Planned Orders
            elif planned_order.order_release_date < today_datetime:
                planned_order_item_list.note = 'Release date in the past'
        # Requirements from Planned Order Explosion
        for mrp_element in list.mrp_parameter_id.mrp_element_ids.filtered(lambda r: r.mrp_origin == "mrp"):
            if not mrp_element.mrp_qty == 0.0:
                self.env['mrp.planning.engine.list.item'].create({
                    'wizard_id' : list.id,
                    "mrp_parameter_id": list.mrp_parameter_id.id,
                    "product_id": mrp_element.product_id.id,
                    "mrp_qty": mrp_element.mrp_qty,
                    "mrp_date": mrp_element.mrp_date,
                    "mrp_type": mrp_element.mrp_type,
                    "mrp_origin": "mrp",
                    "mrp_order_number": mrp_element.mrp_order_number,
                    "parent_product_id": mrp_element.parent_product_id.id,
                    "note": mrp_element.note,
                    "fixed": mrp_element.fixed,
                    "mto_origin": mrp_element.mto_origin,
                })
        # Requirements from Planned Order Stock Transfer
        for mrp_element in list.mrp_parameter_id.mrp_element_ids.filtered(lambda r: r.mrp_origin == "st"):
            if not mrp_element.mrp_qty == 0.0:
                self.env['mrp.planning.engine.list.item'].create({
                    'wizard_id' : list.id,
                    "mrp_parameter_id": list.mrp_parameter_id.id,
                    "product_id": mrp_element.product_id.id,
                    "mrp_qty": mrp_element.mrp_qty,
                    "mrp_date": mrp_element.mrp_date,
                    "mrp_type": mrp_element.mrp_type,
                    "mrp_origin": "st",
                    "mrp_order_number": mrp_element.mrp_order_number,
                    "parent_product_id": False,
                    "note": mrp_element.note,
                    "fixed": mrp_element.fixed,
                    "mto_origin": False,
                })
        list._get_cum_qty()
        return {
            'type': 'ir.actions.act_window',
            'name': _('MRP Planning Engine List'),
            'res_model': 'mrp.planning.engine.list',
            'target': 'main',
            'views': [(self.env.ref('mrp_planning_engine.view_mrp_planning_engine_list_form').id, "form")],
            'res_id': self.id,
        }

    def _get_cum_qty(self):
        for item in self.item_ids:
            item.mrp_qty_cum = 0.0
            logger.info(item.mrp_date)
            logger.info(item.mrp_qty)
            items = self.env['mrp.planning.engine.list.item'].search([('wizard_id', '=', self.id),('mrp_date', '<=', item.mrp_date)])
            item.mrp_qty_cum = sum(items.mapped('mrp_qty'))
            # item.mrp_qty_cum = 9999
        return True
    
    def compute_engine_run_product_id(self):
        mrp_engine_run_obj = self.env['mrp.planning.engine.run']
        mrp_engine_run_id = mrp_engine_run_obj.create({
            "warehouse_id":self.mrp_parameter_id.warehouse_id.id,
            "mrp_parameter_id":self.mrp_parameter_id.id,
        })
        message = mrp_engine_run_id.planning_engine_run_by_parameter_id(self.mrp_parameter_id.warehouse_id,self.mrp_parameter_id)
        t_mess_id = False
        if message:
            t_mess_id = self.env["mrp.planning.message"].create({'name': message}).id
        else:
            t_mess_id = self.env["mrp.planning.message"].create({'name': 'no planning result'}).id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Planning Run Results'),
            'res_model': "mrp.planning.message",
            'res_id': t_mess_id,
            'views': [(self.env.ref('mrp_planning_engine.view_mrp_planning_message_form').id, "form")],
            'target': 'new',
        }


class MRPPlanningEngineListItem(models.TransientModel):
    _name = 'mrp.planning.engine.list.item'
    _description = 'MRP Planning Engine List Item'
    _order = "mrp_date, mrp_type desc, id"

    wizard_id = fields.Many2one('mrp.planning.engine.list', readonly=True)
    mrp_parameter_id = fields.Many2one("mrp.parameter", "MRP Planning Parameters",  readonly=True)
    product_id = fields.Many2one("product.product", readonly=True)
    product_id_default_code = fields.Char(related="product_id.default_code", readonly=True)
    product_uom = fields.Many2one("uom.uom", readonly=True, related="product_id.product_tmpl_id.uom_id")
    release_date = fields.Date("Release Date", readonly=True)
    mrp_date = fields.Date("MRP Date", readonly=True)
    mrp_order_number = fields.Char("Order Number", readonly=True)
    mrp_origin = fields.Selection(MRP_ORIGIN_SELECTION, string="Origin", readonly=True)
    mrp_qty = fields.Float("MRP Quantity", readonly=True)
    doc_qty = fields.Float("Document Quantity", readonly=True)
    mrp_type = fields.Selection(MRP_TYPE_SELECTION, string="Type", readonly=True)
    parent_product_id = fields.Many2one("product.product", string="Parent Product", readonly=True)
    fixed = fields.Boolean("Fixed", readonly=True)
    mrp_qty_cum = fields.Float('Projected Stock Qty', readonly=True)
    forward_mode_indicator = fields.Boolean("Forward Mode", readonly=True)
    rescheduled_due_date = fields.Date("Rescheduled MRP Date", readonly=True)
    delay = fields.Char("Delay (Days)", compute="_get_delay")
    production_id = fields.Many2one("mrp.production", "Manufacturing Order")
    purchase_line_id = fields.Many2one("purchase.order.line", "Purchase Order Line")
    purchase_order_id = fields.Many2one("purchase.order", "Purchase Order")
    state = fields.Selection(STATE_SELECTION, string="State")
    stock_move_id = fields.Many2one("stock.move", string="Stock Move")
    mto_origin = fields.Char('MTO Origin', readonly=True)
    note = fields.Char("Planning Note", readonly=True)

    def _get_delay(self):
        for item in self:
            item.delay = False
            if item.mrp_type == "s" and item.mrp_origin == "op":
                planned_order = self.env['mrp.planned.order'].search([('name', '=', item.mrp_order_number)], limit=1)
                if planned_order:
                    item.delay = planned_order.delay
        return True

    def mrp_convert_planned_order(self):
        for item in self:
            if item.mrp_origin == "op":
                planned_order = self.env['mrp.planned.order'].search([('name', '=', item.mrp_order_number)], limit=1)
                if planned_order:
                    planned_order.mrp_convert_planned_order()
                    return {
                        'type': 'ir.actions.act_window',
                        'name': _('MRP Planning Engine List'),
                        'res_model': 'mrp.planning.engine.list',
                        'target': 'main',
                        'views': [(self.env.ref('mrp_planning_engine.view_mrp_planning_engine_list_form').id, "form")],
                        'res_id': item.wizard_id.id,
                    }
                else:
                    raise UserError(_("Planned Order not found. Please update the list."))
        return True

    def mrp_display_document(self):
        for item in self:
            if item.mrp_origin == "op":
                planned_order = self.env['mrp.planned.order'].search([('name', '=', item.mrp_order_number)], limit=1)
                if planned_order:
                    return {
                        'type': 'ir.actions.act_window',
                        'name': _('Planned Order'),
                        'res_model': 'mrp.planned.order',
                        'target': 'new',
                        'views': [(self.env.ref('mrp_planning_engine.mrp_planned_order_view_form').id, "form")],
                        'res_id': planned_order.id,
                    }
                else:
                    raise UserError(_("Planned Order not found. Please update the list."))
            elif item.mrp_origin == "po":
                purchase_order = self.env['purchase.order'].search([('name', '=', item.mrp_order_number)], limit=1)
                if purchase_order:
                    return {
                        'type': 'ir.actions.act_window',
                        'name': _('Purchase Order'),
                        'res_model': 'purchase.order',
                        'target': 'new',
                        'views': [(self.env.ref('purchase.purchase_order_form').id, "form")],
                        'res_id': purchase_order.id,
                    }
                else:
                    raise UserError(_("Purchase Order not found. Please update the list."))
            elif item.mrp_origin == "mo":
                manufacturing_order = self.env['mrp.production'].search([('name', '=', item.mrp_order_number)], limit=1)
                if manufacturing_order:
                    return {
                        'type': 'ir.actions.act_window',
                        'name': _('Manufacturing Order'),
                        'res_model': 'mrp.production',
                        'target': 'new',
                        'views': [(self.env.ref('mrp.mrp_production_form_view').id, "form")],
                        'res_id': manufacturing_order.id,
                    }
                else:
                    raise UserError(_("Manufacturing Order not found. Please update the list."))
            elif item.mrp_origin == "mv":
                stock_move = self.env['stock.move'].search([('reference', '=', item.mrp_order_number)], limit=1)
                if stock_move:
                    return {
                        'type': 'ir.actions.act_window',
                        'name': _('Stock Picking'),
                        'res_model': 'stock.picking',
                        'target': 'new',
                        'views': [(self.env.ref('stock.view_picking_form').id, "form")],
                        'res_id': stock_move.picking_id.id,
                    }
                else:
                    raise UserError(_("Stock Move not found. Please update the list."))
            else:
                raise UserError(_("Document not found."))
        return True


