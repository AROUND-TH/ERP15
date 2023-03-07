from odoo import models,fields,api,_
import logging

_logger = logging.getLogger(__name__)

class MRPProduction(models.Model):
    _inherit = 'mrp.production'

    excel_imported = fields.Boolean("Import from excel")

    def button_mark_done(self):
        stock_move_obj = self.env['stock.move']
        stock_move_line_obj = self.env['stock.move.line']

        for production in self:
            if production.excel_imported:
                stock_move_id = stock_move_obj.search([('production_id','=',production.id),('product_id','=',production.product_id.id)])
                stock_move_line_id = stock_move_line_obj.search([('move_id','=',stock_move_id.id),('product_id','=',production.product_id.id)])
                stock_move_line_id.unlink()
        return super().button_mark_done()

    def action_confirm(self):
        
        res = super().action_confirm()
        stock_picking_obj = self.env['stock.picking']
        move_ids = []

        for production in self:
            if production.excel_imported:
                stock_warehouse_obj = production.picking_type_id.warehouse_id

                production.write({
                    "qty_producing":production.product_qty,
                })
                for move_raw in production.move_raw_ids:
                    move_line_val = {
                        "name":"New",
                        "product_id":move_raw.product_id.id,
                        "product_uom_qty":move_raw.product_uom_qty,
                        "product_uom":move_raw.product_uom,
                        "location_id":stock_warehouse_obj.lot_stock_id.id,
                        "location_dest_id":stock_warehouse_obj.pbm_loc_id.id,       
                    }
                    move_ids.append(move_line_val)
                stock_picking_id = stock_picking_obj.create({
                    "picking_type_id":stock_warehouse_obj.pbm_type_id.id,
                    "location_id":stock_warehouse_obj.lot_stock_id.id,
                    "location_dest_id":stock_warehouse_obj.pbm_loc_id.id,
                    "scheduled_date":production.date_planned_start_pivot,
                    "date_deadline":production.date_planned_start_pivot,
                    "origin":production.name,
                    "group_id":production.procurement_group_id.id,
                    "move_ids_without_package":move_ids,
                })
                if stock_picking_id:
                    production.write({
                        "picking_ids":[(4,stock_picking_id.id)]
                    })
                    stock_picking_id.write({
                        "group_id":production.procurement_group_id.id,
                    })
                    stock_picking_id.action_confirm()
        return res