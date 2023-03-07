# -*- coding: utf-8 -*-
# Copyright (c) OpenValue All Rights Reserved


from odoo import api, fields, models, _


MRP_ORIGIN_SELECTION = [
    ("so", "Sales Order"),
    ("di", "Demand Item"),
    ("mo", "Manufacturing Order"),
    ("po", "Purchase Order"),
    ("mv", "Move"),
    ("mrp", "Requirements"),
    ("op", "Planned Order"),
    ("st", "Stock Transfer"),
]

MRP_TYPE_SELECTION = [
    ("s", "Supply"),
    ("d", "Demand"),
    ("b", "Begin"),
    ("e", "End"),
]

STATE_SELECTION = [
    ("draft", "Draft"),
    #("cancel", "Cancelled"),
    ("waiting", "Waiting Another Move"),
    ("confirmed", "Waiting Availability"),
    ("partially_available", "Partially Available"),
    ("assigned", "Available"),
    #("done", "Done"),
]


class MrpElement(models.Model):
    _name = "mrp.element"
    _description = "MRP Element"
    _order = "mrp_parameter_id, mrp_date, mrp_type desc, id"


    note = fields.Char("Planning Note")
    mrp_parameter_id = fields.Many2one("mrp.parameter", "MRP Planning Parameters", index=True, required=True)
    warehouse_id = fields.Many2one('stock.warehouse', "Warehouse", related="mrp_parameter_id.warehouse_id", store=True, readonly=True)
    company_id = fields.Many2one("res.company", "Company", related="mrp_parameter_id.warehouse_id.company_id", readonly=True)
    product_id = fields.Many2one("product.product", related="mrp_parameter_id.product_id", store=True, readonly=True)
    release_date = fields.Date("Release Date")
    mrp_date = fields.Date("MRP Date")
    mrp_order_number = fields.Char("Order Number")
    mrp_origin = fields.Selection(MRP_ORIGIN_SELECTION, string="Origin")
    doc_qty = fields.Float("Document Quantity")
    mrp_qty = fields.Float("MRP Quantity")
    mrp_type = fields.Selection(MRP_TYPE_SELECTION, string="Type")
    parent_product_id = fields.Many2one("product.product", string="Parent Product")
    production_id = fields.Many2one("mrp.production", "Manufacturing Order")
    purchase_line_id = fields.Many2one("purchase.order.line", "Purchase Order Line")
    purchase_order_id = fields.Many2one("purchase.order", "Purchase Order")
    fixed = fields.Boolean("Fixed", readonly=True)
    state = fields.Selection(STATE_SELECTION, string="State")
    stock_move_id = fields.Many2one("stock.move", string="Stock Move")
    mto_origin = fields.Char('MTO Origin')
    forward_mode_indicator = fields.Boolean("Forward Mode")
    rescheduled_due_date = fields.Date("Rescheduled MRP Date")

