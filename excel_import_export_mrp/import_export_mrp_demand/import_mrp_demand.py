# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ImportMrpDemand(models.TransientModel):
    _name = 'import.mrp.demand'
    _description = 'ImportMrpDemand'

    # warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse')
    warehouse_name = fields.Char(
        string="Warehouse",
        required=True
    )

    # product_id = fields.Many2one("product.product", 'Product')
    product_code = fields.Char(
        string="Product Code",
        required=True
    )

    date_planned = fields.Datetime('Planned Date', required=True)
    planned_qty = fields.Float("Planned Qty", required=True, digits='Product Unit of Measure')

    # uom_id = fields.Many2one('uom.uom', 'UoM', readonly=True, related='product_id.product_tmpl_id.uom_id')
    uom_name = fields.Char(
        string="UoM"
    )

    status = fields.Char(
        string="Import Status"
    )
    message = fields.Char(
        string="Error Message"
    )

